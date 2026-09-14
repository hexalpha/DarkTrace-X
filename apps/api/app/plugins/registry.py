from dataclasses import dataclass
from typing import Callable


@dataclass(frozen=True)
class PluginManifest:
    id: str
    name: str
    version: str
    capabilities: tuple[str, ...]
    required_scopes: tuple[str, ...]
    network_egress: bool = False


class PluginRegistry:
    """Allowlist-only extension registry. Load third-party code in isolated worker processes."""

    def __init__(self) -> None:
        self._plugins: dict[str, tuple[PluginManifest, Callable | None]] = {}

    def register(self, manifest: PluginManifest, handler: Callable | None = None) -> None:
        if manifest.id in self._plugins:
            raise ValueError(f"Duplicate plugin id: {manifest.id}")
        self._plugins[manifest.id] = (manifest, handler)

    def manifests(self) -> list[PluginManifest]:
        return [value[0] for value in self._plugins.values()]


plugin_registry = PluginRegistry()
plugin_registry.register(PluginManifest(
    id="builtin-asset-correlation", name="Asset Correlation", version="0.1.0",
    capabilities=("ioc.enrich", "asset.correlate"), required_scopes=("intel:read",), network_egress=False,
))
plugin_registry.register(PluginManifest(
    id="builtin-approved-source-monitor", name="Approved Source Monitor", version="0.1.0",
    capabilities=("mention.collect", "exposure.alert"), required_scopes=("sources:read",), network_egress=True,
))

