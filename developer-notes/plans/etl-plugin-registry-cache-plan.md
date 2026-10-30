# Automatic, developer-free plugin registry cache

## Summary

Registry performance could be improved with a manifest, but developers should only use `@PluginRegistry.register(...)`. A hand-maintained manifest is the wrong interface.

The registry should maintain its own cache. Normal plugin execution should use the cache. If the cache does not exist, such as on the first run, the registry should refresh it automatically. If an existing cache does not contain the requested plugin, execution should exit and instruct the user to run `--refresh-registry` to regenerate the cache.

## Proposed behavior

- On startup, load an automatically generated registry index containing:

  - plugin class name;
  - importing module path;
  - package source/version signature.

- When `PluginRegistry.get("PluginName")` is called:

  1. Load the indexed module only.
  2. Let the decorator populate the in-memory registry.
  3. If the plugin is absent from an existing index, exit and instruct the user to run `--refresh-registry`.

- When `--list-plugins` is used, load names from the index without importing every plugin module.

- When `--refresh-registry` is used, rescan configured packages, import modules, collect decorator registrations, and atomically rewrite the generated cache.

## Cache maintenance

The cache should be maintained automatically by the registry/utilities:

- Update entries whenever a decorator registers a plugin.
- Detect changed or newly added plugin files during an explicit registry refresh.
- Refresh automatically when the cache does not exist.
- Treat a stale, corrupt, or incompatible existing cache as unavailable and instruct the user to run `--refresh-registry`.
- Store the cache outside source control, such as the application cache directory, rather than inside the repository.
- Use an atomic write so concurrent ETL processes cannot leave a partial cache.

The explicit refresh option remains useful after deployment changes, packaging changes, or when diagnosing discovery problems.

## Important limitation

A decorator cannot register a class that has never been imported. Therefore, the first run, when no cache exists, must scan/import the package once. After a plugin is added, the existing cache remains unchanged until a user explicitly runs `--refresh-registry`.

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

Adding a new plugin requires no manifest update. The user must run `--refresh-registry` before the new plugin is available through an existing cache.

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
- Missing cache triggers an automatic refresh.
- `--refresh-registry` replaces the temporary cache.
- Existing stale, corrupt, and permission-denied cache files require `--refresh-registry`.
- Separate virtual environments produce separate cache files.

- New plugin file becomes available after `--refresh-registry`.
- Cached plugin loads only its module.
- `--refresh-registry` rebuilds the index.
- Corrupt or stale cache triggers a rebuild.
- `--list-plugins` returns indexed names.
- Duplicate plugin names are reported explicitly.
- Existing decorator, `get()`, `get_metadata()`, and `describe()` behavior remains compatible.
