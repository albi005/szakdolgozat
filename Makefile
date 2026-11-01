.PHONY: pull upload status pdf rclone-config

pull:
	bash scripts/pull.sh

upload:
	bash scripts/upload.sh

status:
	bash scripts/status.sh

pdf:
	bash scripts/pdf.sh

rclone-config:
	bash scripts/rclone-config.sh
