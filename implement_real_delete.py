import sys
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# 1. Real Meta deletion in the publisher
p = "src/meta_api/publishing.py"
src = open(p, encoding="utf-8").read()
method = '''
    # -------------------------------------------------------------
    # Lifecycle: delete a published object (Wave 9.8 — makes "manage
    # posts" TRUE: scheduled drafts are removed locally, published
    # objects are removed from Meta itself)
    # -------------------------------------------------------------
    async def delete_published(self, platform: str, external_id: str) -> Dict[str, Any]:
        """DELETEs a published FB Page post or IG media object via Graph API.
        Honest result dict — never claims success without a 200."""
        platform = (platform or "").lower()
        target = "facebook" if platform in ("facebook", "both") else platform
        if not external_id:
            return {"ok": False, "detail": "no external id"}
        if not self.access_token or self.access_token.startswith("your-"):
            return {"ok": False, "detail": "Meta token not configured (fail-closed)"}
        url = f"{self.BASE_URL}/{external_id}"
        try:
            async with httpx.AsyncClient(timeout=20.0) as client:
                resp = await client.delete(url, params={"access_token": self.access_token})
            if resp.status_code == 200:
                logger.info(f"Deleted published {platform} object {external_id} on Meta")
                return {"ok": True}
            logger.warning(f"Meta delete {platform} {external_id} failed: HTTP {resp.status_code} {resp.text[:180]}")
            return {"ok": False, "detail": f"HTTP {resp.status_code}: {resp.text[:180]}"}
        except Exception as e:
            logger.error(f"Meta delete {platform} {external_id} error: {e}")
            return {"ok": False, "detail": str(e)[:180]}

'''
anchor = "meta_publisher = MetaPublisher()"
assert anchor in src
src = src.replace(anchor, method + anchor, 1)
open(p, "w", encoding="utf-8").write(src)
import ast; ast.parse(src)
print("delete_published added to MetaPublisher")

# 2. The DELETE route performs real removal + local cleanup
p2 = "src/modules/content/routes.py"
src2 = open(p2, encoding="utf-8").read()
old_route = '''@router.delete("/api/content/posts/{post_id}", tags=["Content Studio"])
async def delete_content_post(post_id: str):
    """Deletes a content post."""
    success = content_studio_service.delete_post(post_id)
    if not success:
        raise HTTPException(status_code=404, detail="Post not found or could not be deleted")
    return {"status": "success", "message": f"Post {post_id} deleted successfully"}'''
new_route = '''@router.delete("/api/content/posts/{post_id}", tags=["Content Studio"])
async def delete_content_post(post_id: str):
    """
    Deletes a content post. Wave 9.8 (owner truth-audit): if the post was
    already published, its real Meta objects (meta_post_id) are deleted from
    the Page/IG via Graph API FIRST — the local row is removed and the response
    reports honestly which deletions actually happened.
    """
    import json as _json
    post = content_studio_service.get_post(post_id)
    if not post:
        raise HTTPException(status_code=404, detail="Post not found")

    meta_deleted, meta_errors = {}, {}
    raw_meta = getattr(post, "meta_post_id", None)
    if raw_meta:
        try:
            ids = _json.loads(raw_meta) if isinstance(raw_meta, str) else dict(raw_meta)
        except Exception:
            ids = {}
        from src.meta_api.publishing import meta_publisher
        for platform, ext_id in (ids or {}).items():
            if not ext_id:
                continue
            res = await meta_publisher.delete_published(platform, str(ext_id))
            (meta_deleted if res.get("ok") else meta_errors)[platform] = (
                True if res.get("ok") else res.get("detail"))

    success = content_studio_service.delete_post(post_id)
    if not success:
        raise HTTPException(status_code=500, detail="Post row could not be removed")
    return {
        "status": "success",
        "message": f"Post {post_id} deleted",
        "meta_deleted": meta_deleted,
        "meta_errors": meta_errors,
    }'''
assert old_route in src2
src2 = src2.replace(old_route, new_route, 1)
open(p2, "w", encoding="utf-8").write(src2)
ast.parse(src2)
print("DELETE route now performs real Meta deletion")
