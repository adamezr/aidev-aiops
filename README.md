# AIDev-AIOps

An AWS delivery pipeline where AI reviews every change and investigates production problems, and a person approves every fix before it reaches AWS.

**Demo scenario, "the open door that filled the disk":** a LAMP web server ships with SSH open to the internet and log rotation turned off. The AI review flags both risks before deploy. Later, a simulated brute-force attack floods the logs until the disk fills. An AIOps agent traces the full disk back to the open SSH port and proposes a fix as a pull request, which goes back through review and approval.

Final project for the AI-Driven Cloud Infrastructure course, University of St. Thomas.

## Architecture

```
Commit -> AI review (Claude on Bedrock) -> Human approval -> Deploy (CloudFormation)
   ^                                                              |
   |                                                              v
Human approves PR <- AIOps agent (Lambda + Bedrock) <- Alarm <- Run and monitor
```

## Status

| Phase | Status |
| --- | --- |
| 1. Base site and AI review | In progress |
| 2. Monitoring and attack simulation | Not started |
| 3. AIOps agent | Not started |
| 4. Demo recording | Not started |

## Repository layout

| Path | Purpose |
| --- | --- |
| `infra/lamp-server.yaml` | The LAMP server the pipeline deploys, including the two deliberate demo risks |
| `pipeline/pipeline.yaml` | The delivery pipeline, deployed once by hand |
| `ai-review/review.py` | Sends the template to Claude on Amazon Bedrock and emails the review |
| `ai-review/buildspec.yml` | Runs the review in CodeBuild |

## Deploy the pipeline

Requires the AWS CLI, an EC2 key pair in `us-east-1`, Bedrock access to a Claude model, and a GitHub personal access token with `repo` scope.

```bash
aws cloudformation deploy --region us-east-1 \
  --stack-name aidev-pipeline \
  --template-file pipeline/pipeline.yaml \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    MaintainerEmail=you@example.com \
    KeyName=your-key-pair \
    ModelId=your-claude-model-id \
    GitHubAccessToken=your-token
```

Confirm the SNS subscription email. Each push to `main` then runs the AI review, emails the report, and waits for approval before deploying.

## Tear down

The pipeline creates the `aidev-lamp` stack, so delete it first, then the pipeline.

```bash
aws cloudformation delete-stack --region us-east-1 --stack-name aidev-lamp
aws cloudformation wait stack-delete-complete --region us-east-1 --stack-name aidev-lamp
BUCKET=$(aws cloudformation describe-stacks --region us-east-1 --stack-name aidev-pipeline \
  --query "Stacks[0].Outputs[?OutputKey=='ArtifactBucketName'].OutputValue" --output text)
aws s3 rm "s3://$BUCKET" --recursive
aws cloudformation delete-stack --region us-east-1 --stack-name aidev-pipeline
```
