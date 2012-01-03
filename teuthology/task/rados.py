import contextlib
import logging

from ..orchestra import run

log = logging.getLogger(__name__)

@contextlib.contextmanager
def task(ctx, config):
    """
    Run RadosModel-based integration tests.

    The config should be as follows::

        rados:
          clients: [client list]
          ops: <number of ops>
          objects: <number of objects to use>
          max_in_flight: <max number of operations in flight>
          object_size: <size of objects in bytes>
          min_stride_size: <minimum write stride size in bytes>
          max_stride_size: <maximum write stride size in bytes>
          op_weights: <dictionary mapping operation type to integer weight>

    For example::

        tasks:
        - ceph:
        - rados:
            clients: [client.0]
            ops: 1000
            objects: 25
            max_in_flight: 16
            object_size: 4000000
            min_stride_size: 1024
            max_stride_size: 4096
            op_weights:
              read: 20
              write: 10
              delete: 2
              snap_create: 3
              rollback: 2
              snap_delete: 0
        - interactive:
    """
    log.info('Beginning rados...')
    assert isinstance(config, dict), \
        "please list clients to run on"

    object_size = int(config.get('object_size', 4000000))
    op_weights = config.get('op_weights', {})
    args = [
        'CEPH_CONF=/tmp/cephtest/ceph.conf',
        'LD_LIBRARY_PATH=/tmp/cephtest/binary/usr/local/lib',
        '/tmp/cephtest/enable-coredump',
        '/tmp/cephtest/binary/usr/local/bin/ceph-coverage',
        '/tmp/cephtest/archive/coverage',
        '/tmp/cephtest/binary/usr/local/bin/testrados',
        str(op_weights.get('read', 100)),
        str(op_weights.get('write', 100)),
        str(op_weights.get('delete', 10)),
        str(op_weights.get('snap_create', 0)),
        str(op_weights.get('snap_remove', 0)),
        str(op_weights.get('rollback', 0)),
        str(config.get('ops', 10000)),
        str(config.get('objects', 500)),
        str(config.get('max_in_flight', 16)),
        str(object_size),
        str(config.get('min_stride_size', object_size / 10)),
        str(config.get('max_stride_size', object_size / 5))
        ]

    tests = {}
    for role in config.get('clients', ['client.0']):
        assert isinstance(role, basestring)
        PREFIX = 'client.'
        assert role.startswith(PREFIX)
        id_ = role[len(PREFIX):]
        (remote,) = ctx.cluster.only(role).remotes.iterkeys()
        proc = remote.run(
            args=['CEPH_CLIENT_ID={id_}'.format(id_=id_)] + args,
            logger=log.getChild('rados.{id}'.format(id=id_)),
            stdin=run.PIPE,
            wait=False
            )
        tests[id_] = proc

    try:
        yield
    finally:
        log.info('joining rados')
        run.wait(tests.itervalues())
