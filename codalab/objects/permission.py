'''
Defines ORM classes for groups and permissions.
'''
from codalab.common import NotFoundError, UsageError, PermissionError, IntegrityError
from codalab.lib import spec_util
from codalab.model.tables import (
    GROUP_OBJECT_PERMISSION_ALL,
    GROUP_OBJECT_PERMISSION_READ,
    group_bundle_permission as cl_group_bundle_permission,
    group_object_permission as cl_group_worksheet_permission,
)
from codalab.model.util import LikeQuery
from codalab.objects.permission_utils import permission_str


############################################################


def unique_group(model, group_spec, user_id):
    '''
    Return a group_info corresponding to |group_spec|.
    If |user_id| is given, only search only group that the user is involved in
    (either as an owner or just as a regular member).
    Otherwise, search all groups (this happens when we're root).

    Caution:
    if user_id is None: returns columns of cl_group
    if user_id is not None: returns columns of cl_group natural join cl_user_group

    TODO: function returning different columns based on a flag is not good design

    '''

    def search_all(model, **spec_filters):
        return model.batch_get_groups(**spec_filters)

    def search_user(model, **spec_filters):
        return model.batch_get_all_groups(
            spec_filters, {'owner_id': user_id, 'user_defined': True}, {'user_id': user_id}
        )

    if user_id is None:
        search = search_all
    else:
        search = search_user
    return get_single_group(model, group_spec, search)


def get_single_group(model, group_spec, search_fn):
    '''
    Helper function.
    Resolve a string group_spec to a unique group for the given |search_fn|.
    Throw an error if zero or more than one group matches.
    '''
    if not group_spec:
        raise UsageError('Tried to expand empty group_spec!')
    if spec_util.UUID_REGEX.match(group_spec):
        groups = search_fn(model, uuid=group_spec)
        message = "uuid starting with '%s'" % (group_spec,)
    elif spec_util.UUID_PREFIX_REGEX.match(group_spec):
        groups = search_fn(model, uuid=LikeQuery(group_spec + '%'))
        message = "uuid starting with '%s'" % (group_spec,)
    else:
        spec_util.check_name(group_spec)
        groups = search_fn(model, name=group_spec)
        message = "name '%s'" % (group_spec,)
    if not groups:
        raise NotFoundError('Found no group with %s' % (message,))
    elif len(groups) > 1:
        raise UsageError(
            'Found multiple groups with %s:%s'
            % (message, ''.join('\n  uuid=%s' % (group['uuid'],) for group in groups))
        )
    return groups[0]


############################################################
# Checking permissions


def _check_permissions(model, table, user, object_uuids, owner_ids, need_permission):
    # Validate parameter values
    if table == cl_group_bundle_permission:
        object_type = 'bundle'
    elif table == cl_group_worksheet_permission:
        object_type = 'worksheet'
    else:
        raise IntegrityError('Unexpected table: %s' % table)

    if len(object_uuids) == 0:
        return

    have_permissions = model.get_user_permissions(
        table, user.unique_id if user else None, object_uuids, owner_ids
    )
    if min(have_permissions.values()) >= need_permission:
        return
    if user:
        user_str = '%s(%s)' % (user.name, user.unique_id)
    else:
        user_str = None

    raise PermissionError(
        "User %s does not have sufficient permissions on %s %s (have %s, need %s)."
        % (
            user_str,
            object_type,
            ' '.join(object_uuids),
            ' '.join(map(permission_str, list(have_permissions.values()))),
            permission_str(need_permission),
        )
    )


def check_bundles_have_read_permission(model, user, bundle_uuids):
    _check_permissions(
        model,
        cl_group_bundle_permission,
        user,
        bundle_uuids,
        model.get_bundle_owner_ids(bundle_uuids),
        GROUP_OBJECT_PERMISSION_READ,
    )


def check_bundles_have_all_permission(model, user, bundle_uuids):
    _check_permissions(
        model,
        cl_group_bundle_permission,
        user,
        bundle_uuids,
        model.get_bundle_owner_ids(bundle_uuids),
        GROUP_OBJECT_PERMISSION_ALL,
    )


def check_worksheet_has_read_permission(model, user, worksheet):
    _check_permissions(
        model,
        cl_group_worksheet_permission,
        user,
        [worksheet.uuid],
        {worksheet.uuid: worksheet.owner_id},
        GROUP_OBJECT_PERMISSION_READ,
    )


def check_worksheet_has_all_permission(model, user, worksheet):
    _check_permissions(
        model,
        cl_group_worksheet_permission,
        user,
        [worksheet.uuid],
        {worksheet.uuid: worksheet.owner_id},
        GROUP_OBJECT_PERMISSION_ALL,
    )


def check_bundle_have_run_permission(model, user, bundle):
    try:
        check_bundles_have_all_permission(model, user, [bundle.uuid])
        return True
    except PermissionError:
        return False
