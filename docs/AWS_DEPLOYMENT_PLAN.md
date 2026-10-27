# AWS deployment plan (PROPOSED - nothing is deployed)

Written 2026-10-27. Status: **plan only**. No AWS resource has been created for this project. Every figure marked *estimate* is from
general knowledge of AWS list prices and must be re-checked in the AWS Pricing Calculator before approval.

## 1. What was verified today (read-only calls, profile `portfolio-readonly`)

| Check | Result |
|---|---|
| `sts get-caller-identity` | OK: IAM user `portfolio-readonly`, account `<account id removed>` (matches the historical clue). Credentials never printed. |
| Region | `eu-central-1` (Frankfurt) is configured; not yet confirmed that this account/SCP permits the services below. |
| Cost Explorer, 2026-10-01 to 2026-10-26 | Usage about USD 0.0797, offset by credits of about USD 0.0797; net about 0. |
| Budgets | One budget, "My Zero-Spend Budget", limit USD 1.00, actual 0.0. |
| Free-tier API | Returned no usage rows. |
| `billing:ListBillingViews` | **Denied by an organisation service control policy.** |
| The reported USD 200 credits | **Not verifiable from here.** Credits are visibly being applied, but the remaining balance, expiry and eligible services need the Billing console (Credits page). Do not assume they cover every service. |
| The account is a member of an AWS Organization (SCP present) | Some actions may be blocked by SCPs; this is unknown until tested with a permitted identity. |

The profile is read-only by name and by observed behaviour; provisioning needs a different, explicitly approved identity.

## 2. Hard constraint

The Gradio app has **no authentication**, a global audit tab and in-memory review state (`governance/GRADIO_SECURITY_REVIEW.md`), and Pillow
carries 37 accepted advisories (`governance/PILLOW_ADVISORY_REVIEW.md`). It must **not** be exposed to the public internet in this state.

## 3. Recommended design (simplest, cheapest, no public ingress)

```
 developer laptop --(AWS SSM Session Manager port-forward, IAM-authenticated, TLS)--> EC2 (private, no inbound rules)
                                                                                        docker run governed-claims-engine
                                                                                        bound to 127.0.0.1:7860 on the instance
```

* **Compute:** one small EC2 instance (Graviton `t4g.small` class, *estimate* about USD 12-15/month if left running 24x7; far less if stopped
  between sessions). Alternatives rejected: ECS Fargate or App Runner (public endpoint or extra components), ALB (about USD 16+/month
  and invites public exposure), NAT gateway (about USD 32+/month, not needed), GPUs and paid model endpoints (the assessor is rule-based;
  lexical mode needs no model).
* **Image:** the existing container, built for arm64 or x86_64 to match the instance (current local build is for the laptop architecture; a
  matching build is untested). Delivered via a private ECR repository (storage cost *estimate* under USD 1/month) or `docker save` over SSM.
* **Authn/authz:** access only through SSM Session Manager (IAM identity + MFA). The instance has **no security-group inbound rules**, no
  public IP is needed if VPC endpoints for SSM are used (their hourly cost, *estimate* about USD 7/month each x 3, is more than a public IP,
  so the cheaper compromise is a public IP with zero inbound rules, SSM agent outbound only).
* **Private networking:** default-deny security group; IMDSv2 required; encrypted EBS; the container keeps `read_only`, `cap_drop ALL`,
  non-root, loopback publish.
* **Secrets:** none required (offline, synthetic, no API keys). Do not put any in user data or environment.
* **Logging:** container stdout to CloudWatch Logs with 7-day retention; CloudTrail already exists at organisation level (unverified).
  Audit log stays on the instance in tamper-evident mode; head hash recorded manually off-box.
* **Region rationale:** `eu-central-1` keeps the demo in the EU, matching the Luxembourg/European positioning. No personal data is processed,
  so this is a presentation choice, not a compliance claim.
* **Cost guardrails:** raise the zero-spend budget alert to a deliberate cap (for example USD 10) with email alerts before creating anything.

## 4. Estimated cost (all *estimates*, not verified)

| Item | Running 24x7 | Stopped except 10 h/month |
|---|---|---|
| EC2 t4g.small | about USD 12-15 | about USD 0.2 |
| EBS 16 GB gp3 | about USD 1.5 | about USD 1.5 |
| Public IPv4 | about USD 3.7 | about USD 3.7 (or release when stopped) |
| ECR + CloudWatch Logs | under USD 2 | under USD 1 |
| **Total** | **about USD 18-22** | **about USD 6** |

**Credit applicability: unverified.** AWS credits usually cover EC2, EBS, ECR and CloudWatch but have programme-specific exclusions; confirm on the
Credits page before relying on them.

## 5. Approval gates (nothing proceeds without a yes)

1. Confirm the credit balance, expiry and covered services in the Billing console.
2. Approve the budget cap and the design above (or ask for a cheaper "no AWS at all, video uses local evidence" option).
3. Provide a separate provisioning identity (the read-only profile cannot create resources and should stay read-only).
4. Run an SCP/permission dry run (`--dry-run` on EC2, or Terraform plan) and report any denials.
5. The image vulnerability scan has now been run locally (2026-10-28, `governance/CONTAINER_SCAN_2026-10-28.md`); its critical findings should be resolved or accepted before any deployment (semantic container was run once locally and GitHub Actions is green for the lexical target - `docs/RELEASE_GATES.md`).

## 6. Cleanup (commands to include in any future runbook)

```
aws ec2 terminate-instances --instance-ids <id> --region eu-central-1
aws ecr delete-repository --repository-name governed-claims-engine --force --region eu-central-1
aws logs delete-log-group --log-group-name /governed-claims-engine --region eu-central-1
aws iam delete-instance-profile --instance-profile-name <name>
```

Verify with `aws resourcegroupstaggingapi get-resources --tag-filters Key=project,Values=governed-claims-engine` that nothing remains
(all resources must be tagged `project=governed-claims-engine`).

## 7. What the video may and may not say

May say: a deployment architecture is **proposed**; AWS identity and cost visibility were checked read-only; Docker was validated locally.
May not say: that anything is deployed on AWS, that credits cover it, or that the design is production-ready.
