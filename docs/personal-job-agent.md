# Personal job agent

## Isolation

Develop only on feature/personal-job-agent. Do not merge into master or modify production service settings. Use a private authenticated frontend, a separate backend, and a separate persistent database. Branch previews must never point at the production backend. Store candidate profile, resume files, application answers, credentials, and application history outside Git; this repository is public.

## Candidate policy

Target AI Engineer, AI Support Engineer, and SDE roles at startups, product companies, and MNCs. Candidate is based in Mumbai, authorized to work in India, immediately available, and open to employment, contracting, relocation, and all industries. Foreign relocation requires explicit visa sponsorship; remote jobs must accept India-based candidates. Minimum annual CTC is INR 1,500,000 for Indian employers and USD 70,000 for foreign employers, including foreign remote employers. Do not substitute employer headquarters for the actual hiring entity without evidence. Unknown hiring entity, compensation, geographic eligibility, or sponsorship goes to review. Keep currency and compensation components explicit; do not equate equity estimates or contractor gross revenue with guaranteed cash pay.

Professional employment dates: October 2023 through May 2026. Use exact dates and 2 years 7 months where supported; completed whole years is 2. Never fabricate qualifications or treat project work as professional production experience. Optional demographic disclosures use prefer-not-to-disclose when offered, otherwise remain blank. Required unfamiliar questions go to review.

## Discovery

Desired sources: LinkedIn, Y Combinator, Wellfound, Instahyre, and official employer careers pages/ATS feeds. Implement and report coverage per source; do not claim a source is supported until its adapter works. Prefer supported APIs and public postings. Do not bypass authentication, CAPTCHA, or access restrictions. Normalize and deduplicate source listings against canonical employer requisitions.

Capture source URL, canonical application URL, requisition ID, published timestamp (if supplied), first seen, last checked, role description, location eligibility, compensation evidence, and employer identity. Do not present first-seen dates as publication dates. Recheck the canonical opening immediately before submission. An active careers listing is evidence of an open role, not proof the company will hire.

## Ranking

Initial fit threshold: 7.5/10. Mandatory eligibility gates run independently. Score separately for each role family, considering supported skills, responsibilities, seniority, and professional versus project experience. Explain matched skills, missing skills, uncertainties, and scoring inputs. Calibrate with reviewed examples before unattended operation.

Prioritize fit, recency, credible current hiring activity, and employee review patterns. Record review source, date, sample size, and findings. Sparse reviews mean unknown reputation, not a positive rating. Do not invent hiring or review evidence. Do not fill quotas with weak matches.

## Pilot and approval

The user authorized exactly ONE real initial application. After that, all further submissions remain blocked until explicit user approval. The later target is up to 10 confirmed applications per day, using Asia/Kolkata calendar days. Do not activate that daily mode by default.

Use a persistent transactional reservation before contacting an employer, with a unique canonical requisition constraint. A single pilot reservation must block parallel workers. Reserve one total pilot attempt; if the request outcome is uncertain, block retries and additional applications pending reconciliation. A timeout is not proof of failure. Never retry a potentially submitted application blindly. Record confirmation evidence before marking submitted. Dry runs never count as real submissions and must be visibly labeled.

## Tracker

Store company, role, requisition, source and application links, eligibility and salary evidence, fit score and explanation, resume version, exact submitted answers, submission timestamps, confirmation evidence, and status history. Separate discovered, review-required, ready, reserved, submitting, submitted, failed, unknown-outcome, and withdrawn states. Support pause and an audit trail. Never label a discovered or drafted job as applied.

## Implementation sequence

1. Add owner authentication and isolated private deployment configuration.
2. Add policy configuration, normalized job evidence, and persistent application/status models.
3. Add working discovery adapters, canonical verification, deduplication, and explainable ranking.
4. Add private profile import and resume-grounded draft preparation.
5. Add pilot reservation and submission adapter for one supported application platform.
6. Test concurrent reservation, duplicate jobs, unknown submission outcomes, salary/location/sponsorship rejection, data access isolation, and approval gates.
7. Run dry-run validation, submit the single authorized eligible application, show confirmation, then stop.
8. Enable daily scheduling only after explicit approval; use an always-available worker and persistent database.

## Current limitations

No discovery adapter, offline worker, private deployment, or real submission is implemented by this specification. Repository access alone cannot run builds or submit job applications. Development requires a checkout with a terminal/test runner; live pilot execution additionally requires network/browser access or an authorized submission API and secure account setup. Never commit account sessions or personal profile data to this public branch.
