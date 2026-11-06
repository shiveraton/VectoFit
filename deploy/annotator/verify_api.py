#!/usr/bin/env python3
"""Real HTTP release checks. Creates two invited accounts and ratings in the selected dataset."""

import argparse
import http.cookiejar
import json
import os
import secrets
import urllib.error
import urllib.request


class Browser:
    def __init__(self, base):
        self.base = base.rstrip("/")
        self.jar = http.cookiejar.CookieJar()
        self.opener = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(self.jar)
        )
        self.csrf = None

    def request(self, path, method="GET", data=None, headers=None, expected=(200,)):
        headers = {"Referer": self.base + "/annotator", **(headers or {})}
        if self.csrf:
            headers["X-CSRFToken"] = self.csrf
        payload = None if data is None else json.dumps(data).encode()
        if payload is not None:
            headers["Content-Type"] = "application/json"
        request = urllib.request.Request(
            self.base + path, data=payload, headers=headers, method=method
        )
        try:
            response = self.opener.open(request, timeout=30)
        except urllib.error.HTTPError as exc:
            response = exc
        body = response.read()
        assert response.status in expected, (
            f"{method} {path}: HTTP {response.status} (expected {expected})"
        )
        if "application/json" in response.headers.get("Content-Type", ""):
            body = json.loads(body)
        return body, response

    def initialize(self):
        self.csrf = self.request("/api/annotator/csrf/")[0]["csrfToken"]

    def session(self, dataset):
        return self.request(f"/api/annotator/datasets/{dataset}/session/")[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("base_url")
    parser.add_argument(
        "--dataset",
        type=int,
        required=True,
        help="Authorized small review dataset; writes ratings",
    )
    args = parser.parse_args()
    code = os.environ["ANNOTATOR_TEST_INVITATION_CODE"]
    anonymous = Browser(args.base_url)
    anonymous.request("/api/annotator/me/", expected=(403,))
    anonymous.request("/api/annotator/datasets/", expected=(403,))
    anonymous.request("/api/annotator/login/", "POST", {}, expected=(403,))
    for path in (
        "/admin/",
        "/api/accounts/me/",
        "/api/training/",
        "/api/datasets/",
        "/media/",
        "/dashboard",
        "/training",
    ):
        anonymous.request(path, expected=(403, 404))
    users = []
    for index in range(2):
        browser = Browser(args.base_url)
        browser.initialize()
        username = "release_" + secrets.token_hex(6)
        password = secrets.token_urlsafe(24)
        browser.request(
            "/api/annotator/register/",
            "POST",
            {
                "username": username,
                "email": username + "@example.invalid",
                "password": password,
                "confirm_password": password,
                "invitation_code": code,
            },
            expected=(201,),
        )
        result, _ = browser.request(
            "/api/annotator/login/",
            "POST",
            {"username": username, "password": password},
        )
        browser.csrf = result["csrfToken"]
        browser.request("/api/annotator/me/")
        cookie = next(cookie for cookie in browser.jar if cookie.name == "sessionid")
        assert cookie.secure and cookie.has_nonstandard_attr("HttpOnly"), (
            "HTTPS secure HttpOnly cookie required"
        )
        browser.request("/api/annotator/datasets/999999999/session/", expected=(404,))
        browser.request(
            "/api/annotator/samples/999999999/rating/",
            "PATCH",
            {"knee_annotation": None},
            expected=(404,),
        )
        browser.request("/api/annotator/videos/999999999/", expected=(404,))
        users.append((username, browser))
    sessions = [browser.session(args.dataset) for _, browser in users]
    assert sessions[0]["samples"] and len(sessions[0]["samples"]) == len(
        sessions[1]["samples"]
    )
    for session in sessions:
        for sample in session["samples"]:
            assert sample["knee_annotation"] is None
            assert not ({"classification", "is_correct", "error_label"} & sample.keys())
            assert "classification" not in sample["rep_assessment"]
            assert not (
                {"source_path", "source_label", "filename"}
                & sample["dataset_video"].keys()
            )
    sample = sessions[0]["samples"][0]
    video_path = sample["dataset_video"]["video_url"]
    anonymous.request(video_path, expected=(403,))
    _, video = users[0][1].request(
        video_path, headers={"Range": "bytes=0-31"}, expected=(206,)
    )
    assert video.headers.get("Content-Range", "").startswith("bytes 0-")
    raw_path = os.environ.get("ANNOTATOR_TEST_RAW_MEDIA_PATH")
    if raw_path:
        anonymous.request(raw_path, expected=(403, 404))
    ratings = []
    for grade in ("aligned", "deviated"):
        ratings.append(
            {
                "left": {
                    "grade": grade,
                    "direction": "none" if grade == "aligned" else "valgus",
                },
                "right": {
                    "grade": grade,
                    "direction": "none" if grade == "aligned" else "valgus",
                },
                "symmetry_observation": "symmetric",
                "notes": "Release verification",
            }
        )
    path = f"/api/annotator/samples/{sample['id']}/rating/"
    for (_, browser), rating in zip(users, ratings):
        browser.request(path, "PATCH", {"knee_annotation": rating})
    for (_, browser), rating in zip(users, ratings):
        assert browser.session(args.dataset)["samples"][0]["knee_annotation"] == rating
    users[0][1].request(path, "PATCH", {"knee_annotation": None})
    assert users[0][1].session(args.dataset)["samples"][0]["knee_annotation"] is None
    assert (
        users[1][1].session(args.dataset)["samples"][0]["knee_annotation"] == ratings[1]
    )
    # Complete the small dataset for one rater; the other remains unfinished.
    for row in sessions[0]["samples"]:
        users[0][1].request(
            f"/api/annotator/samples/{row['id']}/rating/",
            "PATCH",
            {"knee_annotation": ratings[0]},
        )
    finished = users[0][1].session(args.dataset)
    assert finished["dataset"]["labelled_sample_count"] == len(finished["samples"])
    for _, browser in users:
        browser.request("/api/annotator/logout/", "POST", {})
        browser.request("/api/annotator/me/", expected=(403,))
    print(
        json.dumps(
            {
                "status": "passed",
                "accounts": [name for name, _ in users],
                "dataset": args.dataset,
                "pending": [
                    "staff and wrong-role credentials",
                    "known existing ineligible IDs",
                    "private owner operations",
                    "Android Chrome",
                    "iPhone Safari",
                    "backup restore",
                ],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
