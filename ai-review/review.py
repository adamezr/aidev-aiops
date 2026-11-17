"""AI coding agent review stage.

Sends the infrastructure template to Claude on Amazon Bedrock, saves the review as
review-report.md, and emails it to the maintainer through SNS before the manual
approval stage. The review is advisory: it never fails the pipeline. A person decides.
"""

import os
import sys
from pathlib import Path

import boto3

MODEL_ID = os.environ["MODEL_ID"]
TOPIC_ARN = os.environ["REVIEW_TOPIC_ARN"]
TEMPLATE_PATH = os.environ.get("TEMPLATE_PATH", "infra/lamp-server.yaml")
COMMIT_ID = os.environ.get("CODEBUILD_RESOLVED_SOURCE_VERSION", "unknown")
REGION = os.environ.get("AWS_REGION", "us-east-1")

PROMPT = """You are a senior cloud infrastructure reviewer in a CI/CD pipeline.
Review this AWS CloudFormation template before a human approves the deployment.

Focus on security, reliability and day-to-day operations, such as open network access,
disk and log management, monitoring gaps, and single points of failure.

Reply in plain text with:
1. A one-line verdict: APPROVE, APPROVE WITH RISKS, or DO NOT APPROVE.
2. Up to five findings, most serious first. For each: severity (HIGH, MEDIUM or LOW),
   the resource name, the problem, and the specific fix.
Keep the whole review under 300 words. Only report problems that are in the template.

Template ({path}):
{template}
"""


def review(template: str) -> str:
    client = boto3.client("bedrock-runtime", region_name=REGION)
    response = client.converse(
        modelId=MODEL_ID,
        messages=[{
            "role": "user",
            "content": [{"text": PROMPT.format(path=TEMPLATE_PATH, template=template)}],
        }],
        inferenceConfig={"maxTokens": 1000, "temperature": 0},
    )
    return response["output"]["message"]["content"][0]["text"].strip()


def main() -> int:
    template = Path(TEMPLATE_PATH).read_text(encoding="utf-8")
    try:
        report = review(template)
    except Exception as error:  # the review must never block a human decision
        report = f"AI review could not run: {error}\nReview the change manually."

    body = (
        f"AI review of commit {COMMIT_ID[:8]}\n"
        f"Template: {TEMPLATE_PATH}\n"
        f"Model: {MODEL_ID}\n\n"
        f"{report}\n\n"
        "The pipeline is now waiting for your approval in CodePipeline."
    )
    Path("review-report.md").write_text(body, encoding="utf-8")
    print(body)

    boto3.client("sns", region_name=REGION).publish(
        TopicArn=TOPIC_ARN,
        Subject=f"AI review: commit {COMMIT_ID[:8]}",
        Message=body,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
