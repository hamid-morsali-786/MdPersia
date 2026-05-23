# Requirements Document

## Introduction

This feature adds a graphical user interface (GUI) to the existing fa-md-pdf project. The GUI provides an alternative way to access all conversion capabilities currently available through the CLI. The CLI remains fully functional and unchanged. The GUI is designed for Windows, follows the project's offline-first philosophy, and supports Persian/RTL layout.

## Glossary

- **GUI_Application**: The graphical user interface window that allows users to configure and execute Markdown-to-PDF conversions without using the command line.
- **CLI**: The existing command-line interface (`fa-md-pdf` command) that remains unchanged and fully operational.
- **Conversion_Engine**: The existing converter module (`converter.py`) that discovers files, builds jobs, and produces PDFs via Playwright/Chromium.
- **File_Picker**: A dialog component within the GUI_Application that allows users to browse and select files or directories.
- **Options_Panel**: The section of the GUI_Application where users configure conversion settings (page format, margins, fonts, Mermaid options, etc.).
- **Progress_Display**: The component within the GUI_Application that shows real-time conversion status, success/failure counts, and error messages.
- **Conversion_Job**: A single file conversion task consisting of a source Markdown file and a target PDF output path.

## Requirements

### Requirement 1: GUI Launch Entry Point

**User Story:** As a user, I want to launch the GUI from the command line or directly, so that I can use the graphical interface without memorizing CLI arguments.

#### Acceptance Criteria

1. WHEN the user runs `fa-md-pdf --gui`, THE GUI_Application SHALL open a window and display the main conversion interface.
2. WHEN the user runs `fa-md-pdf-gui` command, THE GUI_Application SHALL open a window and display the main conversion interface.
3. THE CLI SHALL continue to function identically to its current behavior when `--gui` flag is not provided.
4. WHEN the GUI_Application is launched, THE GUI_Application SHALL detect and use the same offline assets (browsers, fonts, vendor) as the CLI using the existing project root detection logic.

### Requirement 2: Input Selection

**User Story:** As a user, I want to select Markdown files or directories through the GUI, so that I can choose what to convert without typing paths.

#### Acceptance Criteria

1. THE GUI_Application SHALL provide a File_Picker button to select a single Markdown file.
2. THE GUI_Application SHALL provide a File_Picker button to select a directory containing Markdown files.
3. WHEN a directory is selected, THE GUI_Application SHALL display a checkbox to enable or disable recursive file discovery, with recursive enabled by default.
4. WHEN a file or directory is selected, THE GUI_Application SHALL display the resolved absolute path in a text field.
5. THE GUI_Application SHALL allow the user to type or paste a path directly into the input path text field.
6. WHEN an invalid path is entered, THE GUI_Application SHALL display an error message indicating the path does not exist.

### Requirement 3: Output Configuration

**User Story:** As a user, I want to configure where PDFs are saved, so that I can organize my output files.

#### Acceptance Criteria

1. THE GUI_Application SHALL provide a File_Picker button to select an output directory or file path.
2. WHEN no output path is specified, THE GUI_Application SHALL generate PDFs next to the source Markdown files (matching CLI default behavior).
3. WHEN a directory input is used with an output directory, THE GUI_Application SHALL preserve the subdirectory structure in the output.
4. THE GUI_Application SHALL allow the user to type or paste a path directly into the output path text field.

### Requirement 4: Page and Layout Options

**User Story:** As a user, I want to configure page format, margins, and orientation through the GUI, so that I can customize PDF output appearance.

#### Acceptance Criteria

1. THE Options_Panel SHALL provide a dropdown to select page format with options including A4, Letter, and Legal, with A4 selected by default.
2. THE Options_Panel SHALL provide a text field to set page margin with a default value of 15mm.
3. THE Options_Panel SHALL provide a checkbox to enable landscape orientation, with landscape disabled by default.

### Requirement 5: Font Configuration

**User Story:** As a user, I want to configure font settings through the GUI, so that I can control how Persian text appears in the PDF.

#### Acceptance Criteria

1. THE Options_Panel SHALL display the current font-family value, defaulting to the Vazirmatn fallback stack.
2. THE Options_Panel SHALL provide a File_Picker to select a custom font file (.ttf).
3. THE Options_Panel SHALL provide a File_Picker to select a font directory containing Vazirmatn font files.
4. WHEN a font file is selected, THE Options_Panel SHALL disable the font directory picker (matching CLI mutual exclusivity).
5. WHEN the project fonts directory is detected, THE Options_Panel SHALL auto-populate the font directory field.

### Requirement 6: Custom CSS

**User Story:** As a user, I want to provide a custom CSS file through the GUI, so that I can further style the PDF output.

#### Acceptance Criteria

1. THE Options_Panel SHALL provide a File_Picker to select a custom CSS file.
2. WHEN a custom CSS file is selected, THE GUI_Application SHALL append it after the built-in RTL CSS during conversion (matching CLI behavior).

### Requirement 7: Mermaid Diagram Options

**User Story:** As a user, I want to configure Mermaid rendering options through the GUI, so that I can control diagram appearance and behavior.

#### Acceptance Criteria

1. THE Options_Panel SHALL provide a File_Picker to select a local mermaid.min.js file.
2. WHEN the project vendor/mermaid.min.js is detected, THE Options_Panel SHALL auto-populate the Mermaid JS path field.
3. THE Options_Panel SHALL provide a dropdown to select Mermaid theme with options: default, base, dark, forest, neutral, null. The default value SHALL be "default".
4. THE Options_Panel SHALL provide a numeric field to set Mermaid rendering timeout in milliseconds, with a default value of 30000.
5. THE Options_Panel SHALL provide a checkbox to ignore Mermaid errors, with the checkbox unchecked by default.
6. THE Options_Panel SHALL provide an optional text field for a Mermaid CDN URL, which overrides the local file when filled.

### Requirement 8: Advanced Options

**User Story:** As a user, I want to access advanced conversion options through the GUI, so that I have the same control as the CLI.

#### Acceptance Criteria

1. THE Options_Panel SHALL provide a text field to configure Markdown file extensions, defaulting to ".md .markdown".
2. THE Options_Panel SHALL provide a checkbox to keep intermediate HTML files, unchecked by default.
3. THE Options_Panel SHALL provide a checkbox to enable fail-fast mode for batch conversions, unchecked by default.
4. THE Options_Panel SHALL provide a File_Picker to override the Playwright browsers directory path.
5. WHEN the project browsers directory is detected, THE Options_Panel SHALL auto-populate the browsers path field.

### Requirement 9: Conversion Execution

**User Story:** As a user, I want to start the conversion and see progress, so that I know what is happening during batch processing.

#### Acceptance Criteria

1. THE GUI_Application SHALL provide a "Convert" button to start the conversion process.
2. WHEN the "Convert" button is clicked without a valid input path, THE GUI_Application SHALL display an error message and not start conversion.
3. WHILE conversion is in progress, THE Progress_Display SHALL show the name of the file currently being converted.
4. WHILE conversion is in progress, THE Progress_Display SHALL show a progress indicator with the count of completed files out of total files.
5. WHEN a file conversion succeeds, THE Progress_Display SHALL display the source and output paths with a success indicator.
6. WHEN a file conversion fails, THE Progress_Display SHALL display the source path and error message with a failure indicator.
7. WHEN all conversions complete, THE Progress_Display SHALL display a summary showing total succeeded and total failed counts.
8. WHILE conversion is in progress, THE GUI_Application SHALL disable the "Convert" button to prevent duplicate execution.
9. THE GUI_Application SHALL provide a "Cancel" button that becomes active during conversion to allow the user to stop the batch process.

### Requirement 10: RTL Interface Layout

**User Story:** As a user working with Persian documents, I want the GUI to support RTL layout, so that the interface feels natural for Persian users.

#### Acceptance Criteria

1. THE GUI_Application SHALL render its interface with right-to-left text direction.
2. THE GUI_Application SHALL use a Persian-compatible font (Vazirmatn or system fallback) for all interface labels and text.
3. THE GUI_Application SHALL display all labels and messages in Persian.

### Requirement 11: GUI Toolkit and Offline Operation

**User Story:** As a developer, I want the GUI to use a lightweight toolkit that works offline, so that it aligns with the project's offline-first design and minimal dependency philosophy.

#### Acceptance Criteria

1. THE GUI_Application SHALL use a Python GUI toolkit that is included in the Python standard library or requires minimal additional dependencies.
2. THE GUI_Application SHALL operate without any internet connection, consistent with the project's offline-first design.
3. THE GUI_Application SHALL reuse the existing Conversion_Engine (converter.py) without duplicating conversion logic.
4. THE GUI_Application SHALL reuse the existing project root detection and offline asset resolution from defaults.py.

### Requirement 12: Error Handling

**User Story:** As a user, I want clear error messages in the GUI when something goes wrong, so that I can understand and fix issues.

#### Acceptance Criteria

1. IF the Playwright browser is not found, THEN THE GUI_Application SHALL display an error dialog explaining that the browsers directory is missing and how to set it up.
2. IF the Mermaid JS file is not found and no URL is provided, THEN THE GUI_Application SHALL display an error dialog explaining that vendor/mermaid.min.js is missing.
3. IF a selected file or directory does not exist, THEN THE GUI_Application SHALL display an inline error message next to the relevant input field.
4. IF an unexpected error occurs during conversion, THEN THE GUI_Application SHALL display the error message in the Progress_Display without crashing.
