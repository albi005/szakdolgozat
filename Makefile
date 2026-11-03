.PHONY: pull upload status diff pdf rclone-config

pull:
	bash scripts/pull.sh

upload:
	bash scripts/upload.sh

status:
	bash scripts/status.sh

diff:
	bash scripts/diff.sh

pdf:
	bash scripts/pdf.sh

rclone-config:
	bash scripts/rclone-config.sh
