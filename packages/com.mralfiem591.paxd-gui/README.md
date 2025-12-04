# PaxD GUI

A graphical user interface for PaxD package management that provides an easy-to-use interface for installing, updating, and uninstalling PaxD packages.

## Features

- **Package Browser**: View all available packages with search and filtering
- **Installation Status**: Visual indicators showing which packages are installed
- **Package Details**: Detailed information about each package including description, version, and author
- **Batch Operations**: Queue multiple actions and apply them all at once
- **Real-time Updates**: Live progress updates during package operations
- **Error Handling**: Clear error messages and force update options

## Requirements

- Python 3.7+
- PaxD SDK (`com.mralfiem591.paxd-sdk`)
- tkinter (usually included with Python)
- requests

## Installation

Install using PaxD:
```bash
paxd install com.mralfiem591.paxd-gui
```

## Usage

Run the GUI:
```bash
paxd-gui
```

Or run directly:
```bash
python paxd_gui.py
```

## How to Use

1. **Browse Packages**: The left panel shows all available packages. Use the search box to find specific packages.
2. **Filter Packages**: Use the dropdown to filter by installation status (all/installed/not installed).
3. **View Details**: Click on a package to see detailed information in the right panel.
4. **Queue Actions**: Select an action (install/update/uninstall) for each package you want to modify.
5. **Apply Changes**: Click the green "Apply Changes" button to execute all queued actions.
6. **Monitor Progress**: A progress window will show the status of each operation.

## Package Actions

- **Install**: Install a new package
- **Update**: Update an installed package to the latest version
- **Force Update**: Force update even if the package is already up to date
- **Uninstall**: Remove an installed package

## Features in Detail

### Search and Filter
- Search by package name, description, or author
- Filter by installation status
- Real-time search results

### Queue System
- Add multiple actions to a queue
- Review queued actions before applying
- Apply all changes with a single click

### Error Handling
- Clear error messages for failed operations
- Option to force update when packages are already up to date
- Detailed progress logs

### Package Information
- Package name and description
- Version and author information
- Package ID and aliases
- Installation status with visual indicators

## Development

The application is built with:
- **tkinter**: For the GUI framework
- **PaxD SDK**: For package management operations
- **requests**: For fetching package data
- **threading**: For non-blocking operations

### File Structure
- `paxd_gui.py`: Main application entry point
- `gui_components.py`: GUI component classes
- `package_manager.py`: PaxD command execution
- `utils.py`: Utility functions for data processing
- `example.py`: SDK usage examples

## License

MIT License - See LICENSE file for details.

## Contributing

This package is part of the PaxD ecosystem. For bug reports and feature requests, please contact the author or submit issues through the appropriate channels.