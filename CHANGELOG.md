# Changelog

All notable changes to this project will be documented in this file.

## [0.1.9] - 2026-04-10
### Fixed
- Improved configuration UI to automatically disable unified folder selection when Internal storage mode is selected.

## [0.1.8] - 2026-04-10
### Added
- New storage mode options: "Internal" (save to Calibre book folder) and "External" (save to a single unified folder).
- Emblem synchronization now identifies audiobooks in both storage modes.
### Changed
- Refactored `has_audio_format` for better reliability in identifying existing audiobooks.

## [0.1.7] - 2026-04-10
### Added
- Expanded language support to include Portuguese, French, Italian, and Spanish (Spain).
- Improved automatic language detection to support 2-letter and 3-letter ISO 639 codes.
### Changed
- Refactored voice and language selection to use a more maintainable mapping dictionary.

## [0.1.6] - 2026-04-10
### Added
- New configuration option: "Detect language from book metadata".
- Automatic language detection for English and Spanish based on book metadata.

## [0.1.5] - 2026-04-08
### Added
- Initial release with support for Edge TTS and gTTS.
- Basic English and Spanish (Latam) support.
- Background generation and status bar progress tracking.
- Cassette emblem for covers of books with audiobooks.
