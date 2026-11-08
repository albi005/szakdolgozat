.PHONY: init pull pull-finish push push-finish reanchor status pdf dev

# Log in to OneDrive and verify the review document is reachable.
init:
	bash scripts/init.sh

# pull: supervisor suggestions -> thesis.typ.
# Run the agent between the two steps.
pull:
	bash scripts/pull.sh

pull-finish:
	bash scripts/pull_finish.sh

# push: thesis.typ -> DOCX (and git).
# Run the agent between the two steps.
push:
	bash scripts/push.sh

push-finish:
	bash scripts/push_finish.sh

# Repoint the DOCX marker at HEAD after history was rewritten.
reanchor:
	bash scripts/reanchor.sh

status:
	bash scripts/status.sh

pdf:
	bash scripts/pdf.sh

# Single-terminal editing session: typst watch + sioyek + helix.
dev:
	bash scripts/dev.sh
