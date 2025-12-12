# PaxD Default Repository

[![Package Chores](https://github.com/mralfiem591/paxd/actions/workflows/package-chores.yml/badge.svg)](https://github.com/mralfiem591/paxd/actions/workflows/package-chores.yml)

![PaxD Logo](repoasset/logo.png)
![PaxD Ready Badge](repoasset/paxdready.png)

> [!IMPORTANT]
> This repository isnt meant to be cloned unless you are contributing! It is supposed to be used for PaxD to be able to retrieve its packages via its system.

> [!IMPORTANT]
> We know we are a bit early, but **PaxD 26.0.0 HAS BEEN RELEASED!!!** 🎉🎉 This is by far the biggest update PaxD has recieved, and we plan to continue work. You will see the roadmap fill up shortly!

The official default repository for PaxD packages, and home to the official PaxD package.

[Our Website](https://mralfiem591.github.io/paxd)

**Install (or repair) PaxD!**: `curl -L -o %TEMP%\paxd_installer.py https://raw.githubusercontent.com/mralfiem591/paxd/refs/heads/main/paxd-installer.py && python %TEMP%\paxd_installer.py`

Want to use PaxD, without fully installing it? **Try FastxD, the more temporary solution!**: `curl -L -o %TEMP%\fastxd.py https://raw.githubusercontent.com/mralfiem591/paxd/refs/heads/main/fastxd.py && python %TEMP%\fastxd.py`

#### NOTE: both of these, and PaxD itself, **require Python 3.x or above!**
#### You can find a repository to use below, in the "Links" section.

## About

This repository serves as the default package repository for [PaxD](packages/com.mralfiem591.paxd), a command-line package manager. It hosts official packages and provides a centralized location for package distribution and management.

## What is PaxD?

PaxD is a package manager and command-line tool designed to simplify the installation and management of software packages. It provides a streamlined interface for:

- Installing packages from repositories
- Managing dependencies
- Updating installed packages
- Running installed applications

## Getting Started

> [!NOTE]
> PaxD is only compatible with Windows systems ~~at this time~~, and probably only ever will be.

### Installing PaxD

To install PaxD, you'll need Python and pip installed on your system.

The main PaxD package requires the following dependencies:
- Python 3.x
- requests
- colorama
- argparse
- pyyaml
- sentry-sdk

If Python and UV are installed, PaxD can auto-configure its dependencies during installation.

### Using This Repository

Once PaxD is installed, this repository is configured as the default package source. You can install packages using:

```bash
paxd install <package-name>
```

For example:
```bash
paxd install com.mralfiem591.paxd-sdk
paxd install com.mralfiem591.paxd-imageview
```

Or, you can install with package aliases - here are the same 2 packages, using aliases instead:
```bash
paxd install paxd-sdk
paxd install paxd-imageview
```

You can view all aliases in the [resolution file](resolution).

## Package Resolution

The repository includes a comprehensive package resolution system that maps common aliases to package IDs. You can install packages using their full ID or common aliases defined in the [resolution](resolution) file.

## Security

Security is a priority for the PaxD ecosystem. Known vulnerabilities are tracked in the [vulnerabilities](vulnerabilities) file.

> [!TIP]
> Vulnerabilities are also viewable via the Issues tab, tagged with "vulnerability" for easy searching.

> [!CAUTION]
> Ensure you commonly check for vulnerabilites, and update to keep your system safe! They can pop up commonly, and some can be linked to full system compromise, completely remotely.

### Vulnerability Reporting

If you discover a security vulnerability in any package, please report it through the appropriate channels.

### Vulnerability Scanning

You can scan for vulnerabilities by ~~installing the `paxd-vulnscan` tool, via `paxd install paxd-vulnscan`, and~~ running `paxd-vulnscan`.

### Vulnerability Viewing and Searching

Vulnerabilities will be tracked via GitHub Issues. A bot is set up to handle this, and you can easily view them via Issues on the topbar. They are tagged for ease of use, and will be automatically updated if anything happpens.

## Roadmap

You can find our roadmap in the [ROADMAP.md](ROADMAP.md) file. This roadmap is subject to change based on development progress and community feedback.

## Certified & Official Packages

Packages in this repository are marked as:
- **Official**: Maintained by the PaxD team
- **Certified**: Verified and approved packages

The lists of certified and official packages can be found in the [certified](certified) and [official](official) files.

We are working on generating README.md files for each package, which will contain info on if it is certified and/or official.

## Custom Repositories

Want to create a custom repository? Run this command in the directory you want to make a repository in: `curl -L -o create_repo.py https://raw.githubusercontent.com/mralfiem591/paxd/refs/heads/main/create_repo.py && python create_repo.py`

## License

This repository and all packages within it are licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

```
MIT License
Copyright (c) 2025 Alf (mralfiem591)
```

## Contributing

Contributions to the PaxD ecosystem are welcome! Whether you're:
- Reporting bugs
- Suggesting features
- Submitting package updates
- Improving documentation

Please ensure your contributions follow the existing patterns and maintain compatibility with the PaxD package manager.

## Credits

- **Maintainer**: mralfiem591
- **Backend**: Git, GitHub API
- **Frontend**: GitHub

## Links

- Repository: `https://raw.githubusercontent.com/mralfiem591/paxd/refs/heads/main`
- Author: [@mralfiem591](https://github.com/mralfiem591)

## Repository Structure

```
paxd-default-repository/
├── packages/              # All package files
│   ├── com.mralfiem591.paxd/
│   ├── ... other packages
├── repoasset/            # Repository assets (logos, images)
├── paxd                  # Repository metadata
├── certified             # List of certified packages
├── official              # List of official packages
├── resolution            # Package name resolution mappings
├── vulnerabilities       # Known vulnerability database
└── LICENSE               # MIT License
```

---

Made with ❤️ by mralfiem591

> <sub>This app is made possible by your contributions. Feel free to help out!</sub>
> <sub>Licensed under MIT, © mralfiem591 2025.</sub>
