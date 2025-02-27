# Development Guide for Zavepower Integration

This document provides information for developers who want to contribute to or modify the Zavepower Home Assistant integration.

## Development Environment Setup

### Prerequisites

- Git
- Visual Studio Code with Dev Containers extension
- Docker

### Setup Steps

1. Clone the repository:
   ```bash
   git clone https://github.com/osro/zavepower.git
   cd zavepower
   ```

2. Open the project in VS Code and reopen in a Dev Container (VS Code will prompt you for this option, or use the command palette).

3. The container includes everything needed for development, including a Home Assistant instance for testing.

4. Run the development environment:
   ```bash
   scripts/develop
   ```

## Project Structure

- `custom_components/zavepower/`: Main integration directory
  - `__init__.py`: Integration setup
  - `config_flow.py`: Configuration UI flow
  - `const.py`: Constants used across the integration
  - `coordinator.py`: Data coordinator that fetches from the API
  - `sensor.py`: Sensor platform
  - `binary_sensor.py`: Binary sensor platform
  - `entity.py`: Base entity classes
  - `manifest.json`: Integration manifest
  - `translations/`: Translation files for UI

## API Details

The integration communicates with Zavepower's cloud API. Key endpoints include:

- Authentication: Login and token refresh
- System inventory: Getting user's systems
- System state: Getting the current state of a pool system

## Testing

### Manual Testing

1. Make your changes to the code
2. Run the development environment with `scripts/develop`
3. Access Home Assistant at http://localhost:8123
4. Add the Zavepower integration using the UI

### Automated Testing (Future)

Implement tests using the `pytest-homeassistant-custom-component` framework:

```bash
pytest tests/
```

## Debugging

- Check Home Assistant logs for errors
- Enable debug logging for the integration by adding to your `configuration.yaml`:
  ```yaml
  logger:
    default: info
    logs:
      custom_components.zavepower: debug
  ```

## Pull Request Process

1. Create a branch for your feature or bugfix
2. Make your changes with appropriate tests
3. Test your changes thoroughly
4. Ensure the code passes linting (`ruff check .`)
5. Submit a pull request
6. Update documentation if necessary

## Release Process

1. Update version in `custom_components/zavepower/manifest.json`
2. Update CHANGELOG.md with the changes
3. Create a new release on GitHub
4. Tag the release according to semantic versioning

## Resources

- [Home Assistant Developer Documentation](https://developers.home-assistant.io/)
- [Home Assistant Custom Component Development](https://developers.home-assistant.io/docs/creating_component_index)
- [HACS Documentation](https://hacs.xyz/docs/developer/start)