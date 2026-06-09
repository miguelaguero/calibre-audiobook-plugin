PLUGIN_NAME = AudiobookGenerator
VERSION = $(shell python3 -c "import re; m=re.search(r'version\s*=\s*\((\d+),\s*(\d+),\s*(\d+)\)', open('__init__.py').read()); print('.'.join(m.groups()) if m else '0.0.0')")
ZIP_NAME = $(PLUGIN_NAME)-$(VERSION).zip

.PHONY: build clean install

build:
	@echo "Building $(ZIP_NAME)..."
	@rm -f $(ZIP_NAME)
	@zip -r $(ZIP_NAME) \
		__init__.py \
		ui.py \
		config.py \
		worker.py \
		dialogs.py \
		images/ \
		vendor/ \
		plugin-import-name-audiobook_generator.txt \
		-x "**/__pycache__/*" -x "**/*.pyc"
	@echo "Done: $(ZIP_NAME)"

clean:
	@rm -f *.zip

install: build
	calibre-customize -a $(ZIP_NAME)
