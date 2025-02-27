# Zavepower Home Assistant Integration

**⚠️ NOTICE: This project is highly WIP (Work In Progress) ⚠️**

This integration is currently under active development and may have significant changes, bugs, or incomplete features. Use at your own risk in non-production environments.

## Overview

Zavepower is a custom integration for Home Assistant that connects with Zavepower pool control systems. It allows you to monitor and control your pool equipment directly through your Home Assistant instance.

## Features

- Monitor pool system status
- View sensors related to your pool system
- Binary sensors for system state information
- Regular updates from the Zavepower cloud API

## Installation

### HACS (Home Assistant Community Store) - Recommended

1. Make sure you have [HACS](https://hacs.xyz/) installed in your Home Assistant instance
2. Add this repository as a custom repository in HACS:
   - Go to HACS → Integrations → 3 dots in top-right → Custom repositories
   - URL: `https://github.com/osro/zavepower`
   - Category: Integration
3. Search for "Zavepower" in the HACS store and install it
4. Restart Home Assistant

### Manual Installation

1. Copy the `custom_components/zavepower` directory to your Home Assistant `custom_components` directory
2. Restart Home Assistant

## Configuration

1. Go to Home Assistant → Settings → Devices & Services
2. Click "Add Integration" and search for "Zavepower"
3. Follow the configuration flow to enter your Zavepower credentials and select your system

## Entities

This integration provides the following entities:

- **Sensors**: Various measurements from your pool system
- **Binary Sensors**: Status indicators for your pool system

## Troubleshooting

- Check the Home Assistant logs for any errors related to the Zavepower integration
- Verify your credentials and internet connectivity
- Ensure your Zavepower system is online and accessible

## Contributing

Contributions to improve the integration are welcome! Feel free to fork the repository and submit pull requests.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-new-feature`
3. Commit your changes: `git commit -am 'Add some feature'`
4. Push to the branch: `git push origin feature/my-new-feature`
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Disclaimer

This integration is not affiliated with, funded, or in any way associated with Zavepower. It uses the public API to interact with Zavepower services.
