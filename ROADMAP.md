# Roadmap

Welcome to the roadmap of **PaxD**! This document outlines our vision, goals, and planned features for the development of PaxD. Our aim is to create a robust and user-friendly decentralized application that meets the needs of our community.

## Short-term releases roadmap

### Version 26.0.0

#### Uncompleted
| Feature | Description | Status | Priority (/3) |
|-|-|-|-|
| Pulls from external sources | Enable packages to store their package src/ folder in another location, instead of the GitHub repository | 🔴 **Delayed until further notice** | P2 |
| Setup script | Allow packages to have a setup script that runs on installation | 🟠 Planned | P2 |

#### Completed
| Feature | Description | Status | Release Type |
|-|-|-|-|
| Enhanced logging system | Implement a more detailed logging system to track application events and errors |🟢 Completed | Released immediately |
| PaxD SDK | Develop a Software Development Kit (SDK) for PaxD to facilitate package development | 🟢 Completed | Released immediately |
| PaxDP CLI package | Create a command-line interface (CLI) tool for PaxD to streamline package publishing and updating | 🟢 Completed | Released immediately |
| Manifest supports-fastxd flag | Allow packages to specify a `supports-fastxd` flag in their manifest to indicate compatibility with FastxD | 🟢 Completed | Released immediately |
| Improved search indexing | Optimize the search indexing process for faster and more accurate results | 🟢 Completed | Released immediately |
| Replace pip with uv for package dependencies | Switch from using pip to uv for managing Python package dependencies, due to its major speed increase | 🟢 Completed | Released immediately |
| Improved error handling | Enhance error messages and handling throughout the application for better user experience | 🟢 Completed | Released immediately |
| Metapackages support | Introduce support for metapackages, allowing users to install a collection of related packages with a single command | 🟢 Completed | Released immediately |
| PaxD-gui GUI package | Develop a graphical user interface (GUI) for PaxD to enhance user experience for non-terminal users | 🟢 Completed | Released immediately |
| paxd-vulnerability included by default | Integrate paxd-vulnerability scanner into the core PaxD package for improved security | 🟢 Completed | Released immediately |

### Version 26.1.0

**NOTE:** Features listed for version 26.1.0 are not garunteed to be included in the release. They are subject to change based on development progress and community feedback. You may see them delayed or cancelled outright.

#### Uncompleted
| Feature | Description | Status | Priority (/3) |
|-|-|-|-|

#### Completed
| Feature | Description | Status | Release Type |
|-|-|-|-|

**Work has not started on 26.1.0 yet, as we work on the upcoming 26.0.0 release.**

## Long-term releases roadmap

**NOTE: This is a long-term roadmap, and is subject to heavy changes, including delays, early features, and flat-out cancellations.**

### Version 26.2.0

#### Uncompleted
| Feature | Description | Status | Priority (/3)
|-|-|-|-|
| paxdv Virtual Enviroments | Create a system to allow for PaxD to run inside a "virtual enviroment", allowing for packages to be used in one project, not globally. | 🟠 Planned | P2 |

#### Completed
| Feature | Description | Status | Release Type |
|-|-|-|-|

**Work has not started on 2.0.0 yet, as we work on the upcoming 1.7.0, 1.8.0, and 1.9.0 releases. Work is expected to start during 1.9.0 development.**
