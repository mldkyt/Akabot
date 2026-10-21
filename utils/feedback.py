import os

import requests


class Feedback:
    def __init__(self):
        pass

    def create_issue(self, auth_data, title: str, body: str) -> tuple[bool, str]:
        pass


class ForgejoFeedback(Feedback):
    def __init__(self):
        self.instance = os.getenv("FORGEJO_INSTANCE")
        self.token = os.getenv("FORGEJO_TOKEN")
        self.owner = os.getenv("FORGEJO_OWNER")
        self.project = os.getenv("FORGEJO_PROJECT")

    def create_issue(self, auth_data, title: str, body: str) -> tuple[bool, str]:
        if not 4 <= len(title) <= 50:
            return False, "The title has an invalid length"

        if not 10 <= len(body) <= 1200:
            return False, "The body has an invalid length"

        try:
            res = requests.post(f"https://{self.instance}/api/v1/repos/{self.owner}/{self.project}/issues",
                                headers={
                                    "Authorization": f"Bearer {self.token}"
                                }, json={
                    "title": title,
                    "body": f"The user {auth_data['user_name']} ({auth_data['user']}) has submitted an issue through the feedback form:\n\n{body}"
                })
        except Exception as e:
            return False, f"Error occurred when sending request: {e}"

        if res.status_code == 201:
            res_json = res.json()
            return True, res_json["html_url"]
        else:
            print(res.status_code, res.text)
            return False, "The server for tracking issues returned an unknown error, your issue was not submitted. We are sorry for the inconvenience"
