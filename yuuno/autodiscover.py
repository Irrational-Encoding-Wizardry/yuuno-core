import pkg_resources


def discover_environments(module_dict):
    all_exts = []
    for ep in pkg_resources.iter_entry_points('yuuno.environments'):
        module_dict[ep.name] = ep.load()
        all_exts.append(ep.name)
    return all_exts


def discover_extensions():
    for ep in pkg_resources.iter_entry_points('yuuno.extensions'):
        yield ep.load()
