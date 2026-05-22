import requests
from urllib.parse import urlencode
from datetime import datetime

class LinkedInAPI:
    AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
    TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
    API_BASE = "https://api.linkedin.com/v2"
    
    def __init__(self, client_id, client_secret, redirect_uri):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        
    def get_authorization_url(self, state=None):
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'redirect_uri': self.redirect_uri,
            'scope': 'openid profile w_member_social email'
        }
        if state:
            params['state'] = state
        return f"{self.AUTH_URL}?{urlencode(params)}"
        
    def get_access_token(self, authorization_code):
        data = {
            'grant_type': 'authorization_code',
            'code': authorization_code,
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'redirect_uri': self.redirect_uri
        }
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        response = requests.post(self.TOKEN_URL, data=data, headers=headers)
        response.raise_for_status()
        return response.json()
        
    def get_profile(self, access_token):
        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        # Get basic profile using OpenID Connect userinfo endpoint
        response = requests.get(
            'https://api.linkedin.com/v2/userinfo',
            headers=headers
        )
        response.raise_for_status()
        return response.json()
        
    def create_post(self, access_token, author_urn, text, image_url=None):
        """
        Creates a post on LinkedIn using the REST Posts API (Version 202505).
        Handles both Personal Profiles and Organization Pages.
        """
        is_org = "organization" in author_urn

        # Guard: never send a blank post to LinkedIn
        if not text or not text.strip():
            raise ValueError("Post content is empty. Generate content before publishing.")

        # LinkedIn allows up to 3000 chars; only trim if truly over the limit
        commentary = text[:2900] if len(text) > 2900 else text
        
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0',
            'LinkedIn-Version': '202506',
            'X-Restli-Method': 'create'
        }

        # Core payload structure per 202505 specs
        payload = {
            "author": author_urn,
            "commentary": commentary,
            "visibility": "PUBLIC",
            "distribution": {
                "feedDistribution": "MAIN_FEED",
                "targetEntities": [],
                "thirdPartyDistributionChannels": []
            },
            "lifecycleState": "PUBLISHED",
            "isReshareDisabledByAuthor": False
        }


        # Add image content if provided
        if image_url:
            try:
                # 1. Upload the image natively first
                image_urn = self._upload_image(access_token, author_urn, image_url)
                
                # 2. Use media structure for full-size image
                payload["content"] = {
                    "media": {
                        "id": image_urn,
                        "title": "Shared via PostGenius AI"
                    }
                }
            except Exception as e:
                # Image upload failed — post text-only so full text is visible
                with open('linkedin_debug.log', 'a', encoding='utf-8') as f:
                    f.write(f"--- IMAGE UPLOAD FAILED ({datetime.now().isoformat()}) ---\n")
                    f.write(f"Error: {str(e)}\n posting text-only as fallback.\n")
                # Do NOT add content key — text-only posts show full text on LinkedIn

        try:
            with open('linkedin_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"\n--- REST POST ATTEMPT (202505) ---\n")
                f.write(f"Author: {author_urn} | IsOrg: {is_org}\n")

            response = requests.post(
                'https://api.linkedin.com/rest/posts',
                headers=headers,
                json=payload
            )
            
            with open('linkedin_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"REST API Response ({response.status_code}): {response.text[:500]}\n")

            if response.status_code in [200, 201]:
                return response.headers.get('x-restli-id')
            
            # If failed, raise for status
            response.raise_for_status()
            
        except Exception as e:
            with open('linkedin_debug.log', 'a', encoding='utf-8') as f:
                f.write(f"REST POST ERROR: {str(e)}\n")
            raise e

    def _upload_image(self, access_token, author_urn, image_url):
        """
        Downloads an image from URL and uploads it to LinkedIn as a media asset.
        Returns the media URN.
        """
        # 1. Download image
        try:
            img_resp = requests.get(image_url, timeout=30)
            img_resp.raise_for_status()
            img_data = img_resp.content
        except Exception as e:
            raise Exception(f"Image download failed: {str(e)}")

        # 2. Initialize upload
        headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/json',
            'LinkedIn-Version': '202506',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        init_payload = {
            "initializeUploadRequest": {
                "owner": author_urn
            }
        }
        
        init_resp = requests.post(
            'https://api.linkedin.com/rest/images?action=initializeUpload',
            headers=headers,
            json=init_payload
        )
        init_resp.raise_for_status()
        init_data = init_resp.json()
        
        upload_url = init_data['value']['uploadUrl']
        image_urn = init_data['value']['image']
        
        # 3. Upload binary content
        # No LinkedIn-Version or X-Restli headers needed for binary PUT to uploadUrl
        upload_headers = {
            'Authorization': f'Bearer {access_token}',
            'Content-Type': 'application/octet-stream'
        }
        upload_resp = requests.put(upload_url, headers=upload_headers, data=img_data)
        upload_resp.raise_for_status()
        
        return image_urn

    def get_organizations(self, access_token):
        """
        Fetches organizations where the user has a role.
        """
        headers = {
            'Authorization': f'Bearer {access_token}',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        # Fetch organization ACLs
        response = requests.get(
            f"{self.API_BASE}/organizationalEntityAcls?q=roleAssignee",
            headers=headers
        )
        response.raise_for_status()
        data = response.json()
        
        org_urns = [item['organizationalTarget'] for item in data.get('elements', [])]
        
        # Now fetch organization details (name, logo) for each URN
        org_details = []
        for urn in org_urns:
            try:
                # urn is like 'urn:li:organization:12345'
                # We need to extract the ID part or use the whole URN in some endpoints
                org_id = urn.split(':')[-1]
                res = requests.get(
                    f"{self.API_BASE}/organizations/{org_id}",
                    headers=headers
                )
                if res.ok:
                    details = res.json()
                    org_details.append({
                        'id': urn,
                        'name': details.get('localizedName', 'Unknown Page'),
                        'vanityName': details.get('vanityName'),
                        'logo': '' # Logo fetching is more complex, skip for now
                    })
            except:
                continue
                
        return org_details
