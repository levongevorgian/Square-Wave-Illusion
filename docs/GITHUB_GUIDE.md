# Put this project on GitHub

Upload the contents of **square_wave_project**, not the whole course workspace and not only the ZIP file. The ZIP is a transport copy: extract it first. The repository root should contain README.md, model.py, fit.py, docs/, configs/, results/, and .github/.

## Before the professor review

1. Create a repository called `square-wave-illusion` in your GitHub account. A private repository is a sensible starting point for group review, especially while the target and research scope are being discussed.
2. Upload this folder as the repository contents. GitHub Desktop is convenient for preserving the hidden `.github` and `.gitignore` files. The command-line alternative is below.
3. Invite your teammates as collaborators. Share the README and the PDF in docs/ for the first review.
4. Have teammates check the notebook, assumptions, and numerical findings. Track requested changes as issues.
5. After revisions, invite or share with the professor. Use docs/PROFESSOR_REVIEW.md as the discussion checklist.

No repository has been created or uploaded by this package. No collaborator has been contacted. Paper PDFs, professor emails, private paths, credentials, and unpublished collaborator material are not included.

## Command-line alternative

Open a terminal **inside this extracted project folder**. Replace the example remote with the URL of the new empty repository you created. These commands are for you to run; the placeholder is not a real destination.

```sh
git init
git add .
git commit -m "Add square-wave illusion simulation and reference results"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/square-wave-illusion.git
git push -u origin main
```

Create an empty remote repository for this route, without precreating a README, so the first push does not need a merge. Authenticate using your usual GitHub method. See [GitHub's official import instructions](https://docs.github.com/en/migrations/importing-source-code/using-the-command-line-to-import-source-code/adding-locally-hosted-code-to-github).

## What reviewers should open

- README.md: summary, quick start, and current status.
- docs/project_report.pdf: readable review report with figures and numerical results.
- simulation_walkthrough.ipynb: executed explanation of the model and saved fitted results.
- docs/METHODS.md: mathematical and computational details.
- docs/RESULTS.md: result tables and interpretation.
- docs/PROFESSOR_REVIEW.md: choices needing instructor input.

## Authorship and reuse

Confirm the contributor list and a source-code license with the group before presenting the repository as a public research release. No license or final author order has been assigned on your behalf. The package is a review draft, not a journal submission or an approved final course report.
