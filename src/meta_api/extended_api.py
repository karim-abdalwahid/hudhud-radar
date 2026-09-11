"""
Meta Extended APIs: Insights Sync, Threads Publishing, and Marketing (Lead Ads).

Implements the spec v2.1 scopes the owner activated in the Meta Developer app:
1. Insights Sync     — daily Page & Instagram metrics -> page_performance_metrics
2. Threads API       — basic publishing + reading replies (threads_content_publish)
3. Marketing API     — Lead Ads retrieval + campaign performance -> campaigns table

All endpoints degrade gracefully (skip silently) when scopes/tokens are missing.
"""
from typing import Any, Dict, List, Optional
from datetime import date, datetime, timedelta, timezone

import httpx

from src.config import settings
from src.core.logger import logger
from src.core.supabase_client import supabase_db


def _resolve_credentials() -> Dict[str, Optional[str]]:
    """Single source of truth for active Meta credentials (env + Supabase overlay)."""
    token = settings.META_PAGE_ACCESS_TOKEN
    page_id = settings.META_PAGE_ID
    ig_id = settings.META_INSTAGRAM_ACCOUNT_ID
    try:
        cached = supabase_db.get_setting("meta_credentials") or {}
        token = cached.get("page_access_token") or token
        page_id = cached.get("page_id") or page_id
        ig_id = cached.get("instagram_account_id") or ig_id
    except Exception:
        pass
    return {"token": token, "page_id": page_id, "ig_id": ig_id}


class MetaInsightsSync:
    """Syncs daily reach/impressions/engagement metrics into page_performance_metrics."""

    async def sync_recent_metrics(self, days: int = 7) -> Dict[str, Any]:
        creds = _resolve_credentials()
        token = creds["token"]
        if not token or token.startswith("your-"):
            return {"status": "skipped", "reason": "META_PAGE_ACCESS_TOKEN not configured"}

        since = int((datetime.now(timezone.utc) - timedelta(days=days)).timestamp())
        until = int(datetime.now(timezone.utc).timestamp())
        results: Dict[str, Any] = {"facebook": None, "instagram": None}

        async with httpx.AsyncClient(timeout=15.0) as client:
            # Facebook Page Insights (v26 metric names — page_impressions deprecated)
            if creds["page_id"]:
                try:
                    resp = await client.get(
                        f"{settings.META_GRAPH_API_BASE_URL}/{creds['page_id']}/insights",
                        params={
                            "metric": "page_views_total,page_post_engagements,page_follows",
                            "period": "day",
                            "date_preset": "last_7d",
                            "access_token": token,
                        },
                    )
                    if resp.status_code == 200:
                        results["facebook"] = self._store_metric_rows("facebook", resp.json())
                    else:
                        logger.warning(f"FB insights sync failed: {resp.status_code} {resp.text[:200]}")
                except Exception as e:
                    logger.warning(f"FB insights sync error: {e}")

            # Instagram Business Insights (requires instagram_manage_insights scope;
            # falls back to profile-level follower count when scope missing)
            if creds["ig_id"]:
                try:
                    resp = await client.get(
                        f"{settings.META_GRAPH_API_BASE_URL}/{creds['ig_id']}/insights",
                        params={
                            "metric": "reach,views,follower_count",
                            "period": "day",
                            "date_preset": "last_7d",
                            "access_token": token,
                        },
                    )
                    if resp.status_code == 200:
                        results["instagram"] = self._store_metric_rows("instagram", resp.json())
                    else:
                        logger.warning(f"IG insights sync failed ({resp.status_code}) — falling back to profile stats")
                        results["instagram"] = self._store_profile_fallback("instagram", creds["ig_id"], token)
                except Exception as e:
                    logger.warning(f"IG insights sync error: {e}")

        return {"status": "success", "synced": results}

    def _store_profile_fallback(self, platform: str, ig_id: str, token: str) -> int:
        """When insights scope is missing, still record today's follower count."""
        try:
            r = httpx.get(
                f"{settings.META_GRAPH_API_BASE_URL}/{ig_id}",
                params={"fields": "followers_count,media_count", "access_token": token},
                timeout=10.0,
            )
            if r.status_code == 200:
                d = r.json()
                today = date.today().isoformat()
                supabase_db.upsert("page_performance_metrics", {
                    "platform": platform,
                    "metric_date": today,
                    "reach": 0,
                    "impressions": 0,
                    "engagement_rate": 0.0,
                    "followers_count": d.get("followers_count", 0),
                    "leads_captured": 0,
                    "metadata": {"source": "profile_fallback", "media_count": d.get("media_count", 0)},
                }, on_conflict="platform,metric_date")
                return 1
        except Exception as e:
            logger.debug(f"Profile fallback failed: {e}")
        return 0

    def _store_metric_rows(self, platform: str, payload: Dict[str, Any]) -> int:
        """Upserts daily metric rows; returns count of stored days."""
        stored = 0
        daily: Dict[str, Dict[str, Any]] = {}

        for line in payload.get("data", []):
            name = line.get("name", "")
            for point in line.get("values", []):
                end_time = (point.get("end_time") or "")[:10]
                if not end_time:
                    continue
                row = daily.setdefault(end_time, {"reach": 0, "impressions": 0, "followers": 0, "engagement": 0.0})
                value = point.get("value") or 0
                if name in ("page_views", "impressions", "views", "page_views_total"):
                    # page_views_total = profile/tab VIEWS, not reach — stored honestly as impressions
                    row["impressions"] += value if isinstance(value, int) else 0
                elif name == "reach":
                    row["reach"] += value if isinstance(value, int) else 0
                elif name in ("follower_count", "page_follows", "page_daily_follows"):
                    row["followers"] += value if isinstance(value, int) else 0
                elif name in ("page_post_engagements",):
                    row["engagement"] += value if isinstance(value, (int, float)) else 0.0

        for metric_date, row in daily.items():
            engagement_rate = round((row["engagement"] / row["reach"]), 3) if row["reach"] else 0.0
            try:
                supabase_db.upsert("page_performance_metrics", {
                    "platform": platform,
                    "metric_date": metric_date,
                    "reach": row["reach"],
                    "impressions": row["impressions"],
                    "engagement_rate": engagement_rate,
                    "followers_count": row["followers"],
                    "leads_captured": 0,
                    "metadata": {"source": "insights_sync", "synced_at": datetime.now(timezone.utc).isoformat()},
                }, on_conflict="platform,metric_date")
                stored += 1
            except Exception as e:
                logger.warning(f"Metric upsert failed for {platform}/{metric_date}: {e}")

        return stored


class ThreadsPublisher:
    """Basic Meta Threads API integration (publish + read replies + delete + insights).

    Token resolution (Phase 9.7): per-user connections (entitlement-gated)
    when user_id is provided; legacy global token otherwise (compat path).
    """

    @staticmethod
    def _resolve_token(user_id: Optional[str] = None) -> Optional[str]:
        """Per-user token (fail-closed entitlement gate), with legacy global
        fallback while no per-user connections exist (Wave 9.8 interim)."""
        if user_id:
            from src.modules.connections.service import connection_service
            tok = connection_service.get_active_token(user_id, "threads")
            if tok:
                return tok
        from src.meta_api.threads_oauth import get_active_threads_token
        return get_active_threads_token()

    async def publish_thread(self, text: str, link: Optional[str] = None,
                             user_id: Optional[str] = None,
                             reply_to_id: Optional[str] = None) -> Dict[str, Any]:
        token = self._resolve_token(user_id)
        if not token:
            return {
                "status": "skipped",
                "reason": "Threads غير مربوط — اربط حسابك من صفحة الإعدادات (Threads OAuth)",
            }

        full_text = f"{text}\n{link}" if link else text
        async with httpx.AsyncClient(timeout=15.0) as client:
            # 1. Create container
            container_data = {"media_type": "TEXT", "text": full_text[:500],
                              "access_token": token}
            if reply_to_id:
                container_data["reply_to_id"] = reply_to_id
            create = await client.post(
                f"{settings.THREADS_BASE_URL}/me/threads",
                data=container_data,
            )
            if create.status_code != 200:
                return {"status": "error", "detail": create.text[:300]}
            container_id = create.json().get("id")

            # 2. Publish container
            publish = await client.post(
                f"{settings.THREADS_BASE_URL}/me/threads_publish",
                data={"creation_id": container_id, "access_token": token},
            )
            if publish.status_code != 200:
                return {"status": "error", "detail": publish.text[:300]}

            thread_id = publish.json().get("id")
            supabase_db.insert("activity_logs", {
                "action_type": "threads_publish",
                "platform": "system",
                "user_id": user_id,
                "target_id": thread_id or "",
                "status": "success",
                "details": {"text_preview": full_text[:120]},
            })
            return {"status": "success", "thread_id": thread_id}

    async def delete_thread(self, thread_id: str, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Deletes a published Threads post (requires threads_delete scope)."""
        token = self._resolve_token(user_id)
        if not token:
            return {"status": "skipped", "reason": "Threads غير مربوط"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.delete(
                f"{settings.THREADS_BASE_URL}/{thread_id}",
                params={"access_token": token},
            )
            if resp.status_code != 200:
                return {"status": "error", "detail": resp.text[:300]}
            supabase_db.insert("activity_logs", {
                "action_type": "threads_delete",
                "platform": "system",
                "user_id": user_id,
                "target_id": thread_id,
                "status": "success",
                "details": {},
            })
            return {"status": "success", "deleted_id": resp.json().get("deleted_id", thread_id)}

    async def get_account_insights(self, metric: str = "views,likes,replies",
                                   user_id: Optional[str] = None) -> Dict[str, Any]:
        """Account-level Threads insights (requires threads_manage_insights)."""
        token = self._resolve_token(user_id)
        if not token:
            return {"status": "skipped", "reason": "Threads غير مربوط"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{settings.THREADS_BASE_URL}/me/threads_insights",
                params={"metric": metric, "access_token": token},
            )
            if resp.status_code != 200:
                return {"status": "error", "detail": resp.text[:300]}
            return {"status": "success", "insights": resp.json().get("data", [])}

    async def get_thread_replies(self, thread_id: str, limit: int = 20,
                                 user_id: Optional[str] = None) -> Dict[str, Any]:
        token = self._resolve_token(user_id)
        if not token:
            return {"status": "skipped", "reason": "Threads غير مربوط"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{settings.THREADS_BASE_URL}/{thread_id}/replies",
                params={"fields": "id,text,timestamp,username", "limit": limit, "access_token": token},
            )
            if resp.status_code != 200:
                return {"status": "error", "detail": resp.text[:300]}
            return {"status": "success", "replies": resp.json().get("data", [])}


class MarketingLeadsSync:
    """Meta Marketing API: Lead Ads retrieval + campaign performance -> campaigns table."""

    async def sync_lead_forms(self, form_id: Optional[str] = None) -> Dict[str, Any]:
        creds = _resolve_credentials()
        token = creds["token"]
        page_id = creds["page_id"]
        if not token or token.startswith("your-") or not page_id:
            return {"status": "skipped", "reason": "token/page missing"}

        async with httpx.AsyncClient(timeout=20.0) as client:
            # 1. List lead gen forms owned by the page (or use provided form)
            if form_id:
                forms = [{"id": form_id}]
            else:
                forms_resp = await client.get(
                    f"{settings.META_GRAPH_API_BASE_URL}/{page_id}/leadgen_forms",
                    params={"fields": "id,name,leads_count,status", "access_token": token},
                )
                if forms_resp.status_code != 200:
                    return {"status": "error", "detail": forms_resp.text[:300]}
                forms = forms_resp.json().get("data", [])

            total_new = 0
            for form in forms[:10]:
                leads_resp = await client.get(
                    f"{settings.META_GRAPH_API_BASE_URL}/{form['id']}/leads",
                    params={"fields": "id,created_time,field_data", "limit": 50, "access_token": token},
                )
                if leads_resp.status_code != 200:
                    continue
                for lead in leads_resp.json().get("data", []):
                    fields = {f["name"]: f["values"][0] for f in lead.get("field_data", []) if f.get("values")}
                    if self._store_ad_lead(form.get("name", "Lead Form"), lead, fields):
                        total_new += 1
            return {"status": "success", "new_leads": total_new, "forms_checked": len(forms[:10])}

    def _store_ad_lead(self, form_name: str, lead: Dict[str, Any], fields: Dict[str, str]) -> bool:
        """Stores an ad lead with full provenance. Skips if already stored (platform id unique)."""
        existing = supabase_db.select("leads", {"profile_url": f"leadgen:{lead.get('id')}"})
        if existing:
            return False
        supabase_db.insert("leads", {
            "source": "other",
            "full_name": fields.get("full_name") or fields.get("name"),
            "contact_email": fields.get("email"),
            "contact_phone": fields.get("phone_number"),
            "location": fields.get("city"),
            "profile_url": f"leadgen:{lead.get('id')}",
            "data_provenance": {
                "collected_at": datetime.now(timezone.utc).isoformat(),
                "source": f"meta_lead_ads:{form_name}",
                "verification_method": "direct",
                "provenance_notes": ["Imported from Meta Lead Ads (Marketing API)"],
            },
            "is_verified_link": False,
        })
        return True

    async def sync_campaign_insights(self) -> Dict[str, Any]:
        """Pulls ad campaign performance into the campaigns table."""
        creds = _resolve_credentials()
        token = creds["token"]
        if not token or token.startswith("your-"):
            return {"status": "skipped", "reason": "token missing"}
        act_id = getattr(settings, "META_AD_ACCOUNT_ID", None)
        if not act_id:
            return {"status": "skipped", "reason": "META_AD_ACCOUNT_ID not configured"}

        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{settings.META_GRAPH_API_BASE_URL}/act_{act_id}/campaigns",
                params={
                    "fields": "id,name,status,objective,insights{spend,reach,impressions,clicks,actions}",
                    "access_token": token,
                },
            )
            if resp.status_code != 200:
                return {"status": "error", "detail": resp.text[:300]}
            synced = 0
            for camp in resp.json().get("data", []):
                insights = (camp.get("insights") or {}).get("data", [{}])[0] if camp.get("insights") else {}
                messages_sent = 0
                for action in insights.get("actions", []):
                    if action.get("action_type") in ("messaging_conversation_started_7d", "onsite_conversion.messaging_conversation_started_7d"):
                        messages_sent = int(action.get("value", 0))
                if self._upsert_campaign(camp, insights, messages_sent):
                    synced += 1
            return {"status": "success", "campaigns_synced": synced}

    def _upsert_campaign(self, camp: Dict[str, Any], insights: Dict[str, Any], messages_sent: int) -> bool:
        name = camp.get("name", f"Campaign {camp.get('id')}")
        existing = supabase_db.select("campaigns", {"name": name})
        payload = {
            "name": name,
            "platform": "facebook",
            "status": (camp.get("status") or "unknown").lower(),
            "target_criteria": {"objective": camp.get("objective"), "campaign_id": camp.get("id")},
            "total_contacts": int(insights.get("reach", 0) or 0),
            "messages_sent": messages_sent,
            "messages_failed": 0,
        }
        if existing:
            row = existing[0]
            supabase_db.update("campaigns", row["id"], {
                "status": payload["status"],
                "total_contacts": payload["total_contacts"],
                "messages_sent": payload["messages_sent"],
                "target_criteria": payload["target_criteria"],
            })
            return True
        supabase_db.insert("campaigns", payload)
        return True


class ThreadsLeadsSync:
    """
    Threads Replies → CRM Bridge (pull-based, Wave 9.8 step 1).
    Threads has no DM API — customers arrive as REPLIES to published threads.
    This sync pulls recent replies, resolves/creates a lead per author
    (deterministic by threads_account_id, username-keyed fallback), enriches
    the profile via the official Threads API, and stores each reply as a message.
    Zero fabrication: only API-returned fields are stored.
    """

    def __init__(self, db=None, resolver=None, lead_svc=None):
        """Optional dependency injection (defaults resolve lazily — testable)."""
        self._db = db
        self._resolver = resolver
        self._lead_svc = lead_svc

    def _deps(self):
        if self._db is None:
            from src.core.supabase_client import supabase_db
            self._db = supabase_db
        if self._resolver is None:
            from src.identity.resolver import identity_resolver
            self._resolver = identity_resolver
        if self._lead_svc is None:
            from src.leads.service import lead_service
            self._lead_svc = lead_service
        return self._db, self._resolver, self._lead_svc

    @staticmethod
    def _resolve_token(user_id: Optional[str] = None) -> Optional[str]:
        """Per-user Threads token resolution (delegates to the publisher's resolver)."""
        return ThreadsPublisher._resolve_token(user_id)

    @staticmethod
    async def _fetch_threads_profile(author_id: str, token: str) -> Dict[str, Any]:
        """Official Threads user lookup (threads_basic). Any error → empty dict."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    f"{settings.THREADS_BASE_URL}/{author_id}",
                    params={
                        "fields": "username,name,thread_profile_picture_url",
                        "access_token": token,
                    },
                )
                if resp.status_code == 200:
                    return resp.json()
                logger.warning(f"Threads profile lookup failed for {author_id}: HTTP {resp.status_code}")
        except Exception as e:
            logger.warning(f"Threads profile lookup error for {author_id}: {e}")
        return {}

    async def capture_thread_reply(self, reply: Dict[str, Any], token: str,
                                   thread_id: Optional[str] = None,
                                   own_username: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Turns one Threads reply into (or appends to) a lead with its message."""
        from datetime import datetime, timezone as tz
        from src.leads.models import MessageCreate, PlatformSource, SenderType
        from src.identity.extractor import ProfileDataExtractor

        db, resolver, lead_svc = self._deps()

        reply_id = reply.get("id")
        username = reply.get("username")
        author_id = (reply.get("from_user") or {}).get("id") or reply.get("from_user_id")

        if not reply_id or (not username and not author_id):
            logger.warning("Threads reply bridge skipped: no id/author identity.")
            return None

        # Self-reply guard: the owner replying from their own account is NOT a lead
        if username and own_username and username.lower() == str(own_username).lstrip("@").lower():
            return {"status": "skipped", "reason": "self_reply"}

        # Idempotency: one reply → one message ever
        existing_msg = db.select("messages", {"platform_message_id": reply_id})
        if existing_msg:
            return {"lead_id": existing_msg[0].get("lead_id"), "duplicate": True}

        # Official profile enrichment when the author id is available
        profile = {}
        if author_id:
            profile = await self._fetch_threads_profile(author_id, token) or {}

        lead_in = ProfileDataExtractor.extract_from_threads({
            "id": author_id,
            "username": username or profile.get("username"),
            "name": profile.get("name"),
            "thread_profile_picture_url": profile.get("thread_profile_picture_url"),
        })
        lead_record, is_new, queue_id = resolver.resolve_and_save_lead(lead_in)
        lead_id = lead_record["id"]

        sent_at = datetime.now(tz.utc)
        if reply.get("timestamp"):
            try:
                sent_at = datetime.fromisoformat(reply["timestamp"].replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                pass

        message = MessageCreate(
            lead_id=lead_id,
            platform=PlatformSource.THREADS,
            platform_message_id=reply_id,
            sender_type=SenderType.LEAD,
            content=reply.get("text") or "",
            sent_at=sent_at,
            metadata={"type": "thread_reply", "thread_id": thread_id},
        )
        lead_svc.add_message(message)

        logger.info(
            f"Threads reply captured: reply {reply_id} → lead {lead_id} "
            f"(new={is_new}, queue_id={queue_id})"
        )
        return {"lead_id": lead_id, "is_new": is_new, "queue_id": queue_id}

    async def sync_account_replies(self, limit_threads: int = 10, limit_replies: int = 20,
                                   user_id: Optional[str] = None) -> Dict[str, Any]:
        """Pulls recent replies across the account's latest published threads."""
        token = self._resolve_token(user_id)
        if not token:
            return {"status": "skipped", "reason": "Threads غير مربوط"}

        captured, skipped, duplicate, self_replies = 0, 0, 0, 0
        async with httpx.AsyncClient(timeout=15.0) as client:
            # Resolve the connected account's own username once (self-reply guard)
            own_username = None
            try:
                me_resp = await client.get(
                    f"{settings.THREADS_BASE_URL}/me",
                    params={"fields": "username", "access_token": token},
                )
                if me_resp.status_code == 200:
                    own_username = me_resp.json().get("username")
            except Exception:
                pass

            threads_resp = await client.get(
                f"{settings.THREADS_BASE_URL}/me/threads",
                params={"fields": "id,text,timestamp", "limit": limit_threads, "access_token": token},
            )
            if threads_resp.status_code != 200:
                return {"status": "error", "detail": threads_resp.text[:300]}

            for thread in threads_resp.json().get("data", []):
                replies_resp = await client.get(
                    f"{settings.THREADS_BASE_URL}/{thread['id']}/replies",
                    params={"fields": "id,text,timestamp,username", "limit": limit_replies,
                            "access_token": token},
                )
                if replies_resp.status_code != 200:
                    continue
                for reply in replies_resp.json().get("data", []):
                    result = await self.capture_thread_reply(
                        reply, token=token, thread_id=thread["id"],
                        own_username=own_username)
                    if result is None:
                        skipped += 1
                    elif result.get("duplicate"):
                        duplicate += 1
                    elif result.get("reason") == "self_reply":
                        self_replies += 1
                    else:
                        captured += 1

        return {"status": "success", "captured": captured, "duplicates": duplicate,
                "skipped": skipped, "self_replies": self_replies}


    async def get_my_posts(self, limit: int = 10, user_id: Optional[str] = None) -> Dict[str, Any]:
        """Lists the account's recent published threads (for the studio Threads manager)."""
        token = self._resolve_token(user_id)
        if not token:
            return {"status": "skipped", "reason": "Threads غير مربوط"}
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(
                f"{settings.THREADS_BASE_URL}/me/threads",
                params={"fields": "id,text,timestamp", "limit": limit, "access_token": token},
            )
            if resp.status_code != 200:
                return {"status": "error", "detail": resp.text[:300]}
            return {"status": "success", "posts": resp.json().get("data", [])}


meta_insights_sync = MetaInsightsSync()
threads_publisher = ThreadsPublisher()
threads_leads_sync = ThreadsLeadsSync()
marketing_leads_sync = MarketingLeadsSync()
