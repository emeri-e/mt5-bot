def get_recaptcha_token(self, sitekey, page_url=None,page_text=None, method='v2'):
        if method == 'v2':
            return self.solve_recaptcha_v2_invisible(sitekey, page_url)#,page_text)
        else:
            return self.solve_with_capsolver(sitekey, page_url)

    def solve_with_capsolver(self, sitekey, page_url):

        if not page_url:
            raise ValueError("page_url is required when using CapSolver")

        api_key = base.api_key
        proxy_string = f"{base.proxy_ip}:{base.proxy_port}:{base.proxy_user}:{base.proxy_password}"

        # Extract cookies from current session
        cookies_list = [
            {"name": c.name, "value": c.value}
            for c in self.session.cookies
            if c.domain in page_url
        ]
        payload = {
            "clientKey": api_key,
            "task": {
                "type": "RecaptchaV3Task",
                "websiteURL": page_url,
                "websiteKey": sitekey,
                "pageAction": "submit",
                "isSession": True,  
                "proxy": proxy_string,
                "cookies": cookies_list

            }
        }

        # Create task
        create_resp = requests.post("https://api.capsolver.com/createTask", json=payload).json()
        task_id = create_resp.get("taskId")

        if not task_id:
            raise Exception(f"CapSolver task creation failed: {create_resp}")

        # Poll result
        result_payload = {
            "clientKey": api_key,
            "taskId": task_id
        }

        import time
        for _ in range(30):
            resp = requests.post("https://api.capsolver.com/getTaskResult", json=result_payload).json()
            if resp.get("status") == "ready":
                return resp["solution"]["gRecaptchaResponse"]
            time.sleep(2)

        raise TimeoutError("CapSolver did not return a result in time.")

    def solve_recaptcha_v2_invisible(self, sitekey: str, page_url: str):
        """
        Solves invisible Recaptcha v2 using CapSolver with a proxy and session cookies.
        Returns the g-recaptcha-response token.
        """
        proxy_string = f"{base.proxy_ip}:{base.proxy_port}:{base.proxy_user}:{base.proxy_password}"

        # Extract cookies from current session
        cookies_list = [
            {"name": c.name, "value": c.value}
            for c in self.session.cookies
            if c.domain in page_url
        ]

        payload = {
            "clientKey": base.api_key,
            "task": {
                "type": "ReCaptchaV2Task",
                "websiteURL": page_url,
                "websiteKey": sitekey,
                "isInvisible": True,
                "isSession": True,  # <--- this enables session support
                "proxy": proxy_string,
                "cookies": cookies_list
            }
        }

        # 1. Create task
        resp = requests.post("https://api.capsolver.com/createTask", json=payload).json()
        if "taskId" not in resp:
            raise Exception(f"CapSolver createTask failed: {resp}")
        
        task_id = resp["taskId"]

        # 2. Poll result
        for _ in range(25):
            result = requests.post("https://api.capsolver.com/getTaskResult", json={
                "clientKey": base.api_key,
                "taskId": task_id
            }).json()

            if result.get("status") == "ready":
                token = result["solution"]["gRecaptchaResponse"]
                
                # Optional: set recaptcha-ca-t session cookie from response
                ca_cookie = result["solution"].get("recaptcha_ca_t")
                if ca_cookie:
                    self.session.cookies.set("recaptcha-ca-t", ca_cookie)

                return token

            time.sleep(2)

        raise TimeoutError("CapSolver Recaptcha v2 (invisible) token not returned in time.")