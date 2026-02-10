#!/usr/bin/env python3
"""
End-to-end test for the build and publish workflow.

Tests:
1. Login
2. Check/create project
3. Upload base map asset
4. Upload overlay SVG
5. Import SVG overlays
6. Run build
7. Check build status
8. Run publish
9. Verify release
"""
import asyncio
import time
import httpx
from pathlib import Path

API_URL = "http://localhost:8000/api"

# Test credentials (from .env or defaults)
TEST_EMAIL = "admin@example.com"
TEST_PASSWORD = "admin123"

# Test project
PROJECT_SLUG = "sedra-3"


async def main():
    async with httpx.AsyncClient(timeout=60.0) as client:
        print("=" * 60)
        print("E2E Build & Publish Test")
        print("=" * 60)

        # 1. Login
        print("\n1. Logging in...")
        try:
            resp = await client.post(f"{API_URL}/auth/login", json={
                "email": TEST_EMAIL,
                "password": TEST_PASSWORD
            })
            resp.raise_for_status()
            tokens = resp.json()
            access_token = tokens["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            print(f"   ✓ Logged in as {TEST_EMAIL}")
        except Exception as e:
            print(f"   ✗ Login failed: {e}")
            return

        # 2. Get project info
        print("\n2. Getting project info...")
        try:
            resp = await client.get(f"{API_URL}/projects/{PROJECT_SLUG}", headers=headers)
            resp.raise_for_status()
            project = resp.json()
            print(f"   ✓ Project: {project['name']} ({project['slug']})")

            # Find draft version
            versions = project.get("versions", [])
            draft_version = next((v for v in versions if v["status"] == "draft"), None)
            if not draft_version:
                print("   Creating new version...")
                resp = await client.post(f"{API_URL}/projects/{PROJECT_SLUG}/versions", headers=headers)
                resp.raise_for_status()
                draft_version = resp.json()
                print(f"   ✓ Created version {draft_version['version_number']}")
            else:
                print(f"   ✓ Using draft version {draft_version['version_number']}")

            version_number = draft_version["version_number"]
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            return

        # 3. Check existing assets
        print("\n3. Checking existing assets...")
        try:
            resp = await client.get(f"{API_URL}/projects/{PROJECT_SLUG}/assets", headers=headers)
            resp.raise_for_status()
            assets_data = resp.json()
            assets = assets_data.get("assets", [])

            base_maps = [a for a in assets if a["asset_type"] == "base_map"]
            overlay_svgs = [a for a in assets if a["asset_type"] == "overlay_svg"]

            print(f"   ✓ Found {len(base_maps)} base map(s), {len(overlay_svgs)} overlay SVG(s)")

            for bm in base_maps:
                print(f"     - Base map: {bm['filename']} (level: {bm.get('level', 'project')})")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            return

        # 4. Check existing overlays
        print("\n4. Checking existing overlays...")
        try:
            resp = await client.get(f"{API_URL}/projects/{PROJECT_SLUG}/overlays", headers=headers)
            resp.raise_for_status()
            overlays_data = resp.json()
            total_overlays = overlays_data.get("total", 0)
            print(f"   ✓ Found {total_overlays} overlay(s)")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            return

        # 5. Build validation
        print("\n5. Validating build...")
        try:
            resp = await client.get(
                f"{API_URL}/projects/{PROJECT_SLUG}/versions/{version_number}/build/validate",
                headers=headers
            )
            resp.raise_for_status()
            validation = resp.json()
            print(f"   Valid: {validation['valid']}")
            print(f"   Base maps: {validation.get('base_map_count', 0)}")
            print(f"   Overlays: {validation.get('overlay_count', 0)}")
            if validation.get("errors"):
                print(f"   Errors: {validation['errors']}")
            if validation.get("warnings"):
                print(f"   Warnings: {validation['warnings']}")

            if not validation["valid"]:
                print("   ✗ Build validation failed, cannot proceed")
                return
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            return

        # 6. Start build
        print("\n6. Starting build job...")
        try:
            resp = await client.post(
                f"{API_URL}/projects/{PROJECT_SLUG}/versions/{version_number}/build",
                headers=headers
            )
            resp.raise_for_status()
            build_job = resp.json()
            job_id = build_job["job_id"]
            print(f"   ✓ Build job started: {job_id}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            return

        # 7. Poll build job status
        print("\n7. Waiting for build to complete...")
        while True:
            try:
                resp = await client.get(f"{API_URL}/jobs/{job_id}", headers=headers)
                resp.raise_for_status()
                job = resp.json()

                status = job["status"]
                progress = job.get("progress", 0)
                message = job.get("message", "")

                print(f"   [{progress:3}%] {status}: {message}")

                if status == "completed":
                    result = job.get("result", {})
                    build_id = result.get("build_id")
                    preview_url = result.get("preview_url")
                    print(f"   ✓ Build completed!")
                    print(f"     Build ID: {build_id}")
                    print(f"     Preview URL: {preview_url}")
                    print(f"     Tiles: {result.get('tiles', {}).get('total_count', 0)} tiles generated")
                    break
                elif status == "failed":
                    print(f"   ✗ Build failed: {job.get('error', 'Unknown error')}")
                    return

                await asyncio.sleep(2)
            except Exception as e:
                print(f"   ✗ Failed to poll job: {e}")
                return

        # 8. Check build status endpoint
        print("\n8. Checking build status...")
        try:
            resp = await client.get(
                f"{API_URL}/projects/{PROJECT_SLUG}/versions/{version_number}/build/status",
                headers=headers
            )
            resp.raise_for_status()
            build_status = resp.json()
            print(f"   Has build: {build_status['has_build']}")
            if build_status["has_build"]:
                print(f"   Build ID: {build_status.get('build_id')}")
                print(f"   Overlays: {build_status.get('overlay_count', 0)}")
                tiles = build_status.get("tiles", {})
                print(f"   Tile levels: {tiles.get('levels', [])}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            return

        # 9. Publish validation
        print("\n9. Validating publish...")
        try:
            resp = await client.get(
                f"{API_URL}/projects/{PROJECT_SLUG}/versions/{version_number}/publish/validate",
                headers=headers
            )
            resp.raise_for_status()
            validation = resp.json()
            print(f"   Valid: {validation['valid']}")
            if validation.get("errors"):
                print(f"   Errors: {validation['errors']}")
            if validation.get("warnings"):
                print(f"   Warnings: {validation['warnings']}")

            if not validation["valid"]:
                print("   ✗ Publish validation failed")
                return
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            return

        # 10. Start publish
        print("\n10. Starting publish job...")
        try:
            resp = await client.post(
                f"{API_URL}/projects/{PROJECT_SLUG}/versions/{version_number}/publish",
                headers=headers
            )
            resp.raise_for_status()
            publish_job = resp.json()
            job_id = publish_job["job_id"]
            print(f"   ✓ Publish job started: {job_id}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            return

        # 11. Poll publish job status
        print("\n11. Waiting for publish to complete...")
        while True:
            try:
                resp = await client.get(f"{API_URL}/jobs/{job_id}", headers=headers)
                resp.raise_for_status()
                job = resp.json()

                status = job["status"]
                progress = job.get("progress", 0)
                message = job.get("message", "")

                print(f"   [{progress:3}%] {status}: {message}")

                if status == "completed":
                    result = job.get("result", {})
                    release_id = result.get("release_id")
                    release_url = result.get("release_url")
                    print(f"   ✓ Publish completed!")
                    print(f"     Release ID: {release_id}")
                    print(f"     Release URL: {release_url}")
                    print(f"     Overlays: {result.get('overlay_count', 0)}")
                    print(f"     Tiles copied: {result.get('tiles_copied', 0)}")
                    break
                elif status == "failed":
                    print(f"   ✗ Publish failed: {job.get('error', 'Unknown error')}")
                    return

                await asyncio.sleep(2)
            except Exception as e:
                print(f"   ✗ Failed to poll job: {e}")
                return

        # 12. Verify project state
        print("\n12. Verifying final state...")
        try:
            resp = await client.get(f"{API_URL}/projects/{PROJECT_SLUG}", headers=headers)
            resp.raise_for_status()
            project = resp.json()

            print(f"   Current release: {project.get('current_release_id', 'None')}")

            versions = project.get("versions", [])
            published = [v for v in versions if v["status"] == "published"]
            print(f"   Published versions: {len(published)}")
        except Exception as e:
            print(f"   ✗ Failed: {e}")
            return

        print("\n" + "=" * 60)
        print("E2E Test Complete!")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
