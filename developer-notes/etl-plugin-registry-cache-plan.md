# Automatic, developer-free plugin registry cache

## Summary

Registry performance could be improved with a manifest, but developers should only use `@PluginRegistry.register(...)`. A hand-maintained manifest is the wrong interface.

The registry should maintain its own cache. Normal plugin execution should use the cache.  Cache misses should exit and request that a user perform `--refresh-registry` that can provide an explicit command to regenerate the registry or add newly developed plugins to the manifest, unless the cache does not exist (e.g., first run) in which case, the registry refresh should be excuted.

## Proposed behavior

- On startup, load an automatically generated registry index containing:

  - plugin class name;
  - importing module path;
  - package source/version signature.

- When `PluginRegistry.get("PluginName")` is called:

  1. Load the indexed module only.
  2. Let the decorator populate the in-memory registry.
  3. If the plugin is absent from the index, perform a full package discovery.
  4. Retry the lookup once.
  5. Raise the existing `KeyError` if it is still unavailable.

- When `--list-plugins` is used, load names from the index without importing every plugin module.

- When `--refresh-registry` is used, rescan configured packages, import modules, collect decorator registrations, and atomically rewrite the generated cache.

## Cache maintenance

The cache should be maintained automatically by the registry/utilities:

- Update entries whenever a decorator registers a plugin.
- Detect changed or newly added plugin files using package metadata or file signatures.
- Automatically refresh on a plugin lookup miss.
- Treat a missing, stale, corrupt, or incompatible cache as a cache miss and rebuild it.
- Store the cache outside source control, such as the application cache directory, rather than inside the repository.
- Use an atomic write so concurrent ETL processes cannot leave a partial cache.

The explicit refresh option remains useful after deployment changes, packaging changes, or when diagnosing discovery problems.

## Important limitation

A decorator cannot register a class that has never been imported. Therefore, the first discovery after adding a plugin must still scan/import the package once. The cache eliminates that cost on subsequent processes, and the automatic lookup-miss refresh means developers do not need to remember any maintenance step.

## Scope of implementation

- Add cache/index management around `register_package_plugins()` in [`components/niagads/etl/utils.py`]( /home/allenem/projects/genomicsdb/niagads-pylib/components/niagads/etl/utils.py:46 ).
- Keep `PluginRegistry.register()` as the only developer-facing registration mechanism.
- Add registry-loading methods to [`components/niagads/etl/plugins/registry.py`]( /home/allenem/projects/genomicsdb/niagads-pylib/components/niagads/etl/plugins/registry.py:16 ).
- Add `--refresh-registry` to the plugin runner.
- Preserve existing behavior and error messages for valid plugins and unresolved plugin names.
- Keep process-local loaded-package caching even with the persistent index.

## Ephemeral registry cache

Use a generated cache file in the active environment’s temporary directory. Nothing should be written to the repository or maintained by developers.

### Cache location

Create the cache under `tempfile.gettempdir()`, with a filename scoped to the runtime environment, for example:

`<temp-dir>/niagads-etl-registry-<environment-hash>.json`

The hash should include the configured plugin package names and the active Python environment (`sys.prefix`) so virtual environments and package sets do not share incompatible indexes.

The cache should:

- be ignored by source control naturally;
- use restrictive file permissions;
- be safe to delete at any time;
- be rewritten atomically;
- expire naturally when the working environment cleans temporary files.

### Runtime behavior

- Reuse the cache when it exists and is valid.
- Automatically rebuild it when a requested plugin is missing.
- Provide `--refresh-registry` to force regeneration.
- Fall back to full discovery if the cache is missing, corrupt, stale, or unreadable.
- Keep a process-local set of already-loaded packages to avoid repeated scans within one process.

Developers continue using only the decorator:

```python
@PluginRegistry.register(metadata)
class MyPlugin(...):
    ...
```

Adding a new plugin requires no manifest update and no explicit refresh; the first lookup miss triggers discovery and refreshes the temporary cache.

### Implementation changes

- Add temporary-cache index handling to `components/niagads/etl/utils.py`.
- Let `PluginRegistry.register()` update the in-memory registry and discovered module index.
- Add `--refresh-registry` to the plugin runner.
- Keep the cache format internal and disposable.
- Do not add generated files, manifests, or cache artifacts to the repository.

## Tests

> NO creating py-tests or now.  

- Cache is created outside the repository.
- A cached plugin loads without scanning all modules.
- Adding a plugin is detected automatically after a lookup miss.
- `--refresh-registry` replaces the temporary cache.
- Deleted, stale, corrupt, and permission-denied cache files recover through discovery.
- Separate virtual environments produce separate cache files.

- New plugin file discovered automatically after a lookup miss.
- Cached plugin loads only its module.
- `--refresh-registry` rebuilds the index.
- Corrupt or stale cache triggers a rebuild.
- `--list-plugins` returns indexed names.
- Duplicate plugin names are reported explicitly.
- Existing decorator, `get()`, `get_metadata()`, and `describe()` behavior remains compatible.
