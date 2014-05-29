from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from contextlib import contextmanager
from copy import copy
from urlparse import urlunparse
import json
import time
import threading

from ws4py.client.threadedclient import WebSocketClient


# =============================================================================
# = Utilities                                                                 =
# =============================================================================

def exists(obj):
    return obj is not None

def nexists(iterable):
    return sum(1 for i in iterable if exists(i))


# =============================================================================
# = Messages                                                                  =
# =============================================================================

class Message(object):
    pass


# = Client messages ===========================================================

class ClientMessage(Message):
    pass


class ConnectMessage(ClientMessage):
    def __init__(self, version, support=None, session=None):
        super(ConnectMessage, self).__init__()

        if support is not None:
            support = list(support)

            # It appears that the preferred version does not need to be
            # in the list of supported version. So, remove it as save a
            # few bytes.
            if version in support:
                support.remove(version)

            # Also, it appears that support can be omitted.
            if not support:
                support = None

        self._version = version
        self._support = support
        self._session = session

    def __eq__(self, other):
        return (self.version == other.version
                and self._support == other._support
                and self._session == other._session)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            'ConnectMessage('
            'version={!r}, '
            'support={!r}, '
            'session={!r})'
        ).format(
            self._version,
            self._support,
            self._session,
        )

    @property
    def version(self):
        return self._version

    @property
    def support(self):
        if not self.has_support():
            raise AttributeError('connect message has no `support` field')
        return self._support

    @property
    def session(self):
        if not self.has_session():
            raise AttributeError('connect message has no `session` field')
        return self._session

    def has_support(self):
        return self._support is not None

    def has_session(self):
        return self._session is not None


class MethodMessage(ClientMessage):
    def __init__(self, id_, method, params):
        super(ClientMessage, self).__init__()
        self._id = id_
        self._method = method
        self._params = copy(params)

    def __eq__(self, other):
        return (self._id == other._id
                and self._method == other._method
                and self._params == other._params)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            'MethodMessage('
            'id_={!r}, '
            'method={!r}, '
            'params={!r})'
        ).format(
            self._id,
            self._method,
            self._params,
        )

    @property
    def id_(self):
        return self._id

    @property
    def method(self):
        return self._method

    @property
    def params(self):
        return copy(self._params)


class SubMessage(ClientMessage):
    def __init__(self, id_, name, params=None):
        super(SubMessage, self).__init__()
        self._id = id_
        self._name = name
        self._params = copy(params)

    def __eq__(self, other):
        return (self._id == other._id
                and self._name == other._name
                and self._params == other._params)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            'SubMessage('
            'id_={!r}, '
            'name={!r}, '
            'params={!r})'
        ).format(
            self._id,
            self._name,
            self._params
        )

    @property
    def id_(self):
        return self._id

    @property
    def name(self):
        return self._name

    @property
    def params(self):
        if not self.has_params():
            raise AttributeError('sub message has no `params` field')
        return self._params

    def has_params(self):
        return self._params is not None


class UnsubMessage(ClientMessage):
    def __init__(self, id_):
        super(UnsubMessage, self).__init__()
        self._id = id_

    def __eq__(self, other):
        return self._id == other._id

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return 'UnsubMessage(id_={!r})'.format(self._id)

    @property
    def id_(self):
        return self._id


# = Server messages ===========================================================

class ServerMessage(Message):
    pass


class AddedMessage(ServerMessage):
    def __init__(self, collection, id_, fields=None):
        self._collection = collection
        self._id = id_
        self._fields = copy(fields)

    def __eq__(self, other):
        return (self._collection == other._collection
                and self._id == other._id
                and self._fields == other._fields)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            'AddedMessage('
            'collection={!r}, '
            'id_={!r}, '
            'fields={!r})'
        ).format(
            self._collection,
            self._id,
            self._fields,
        )

    @property
    def collection(self):
        return self._collection

    @property
    def id_(self):
        return self._id

    @property
    def fields(self):
        if not self.has_fields():
            raise AttributeError('added message has no `added` field')
        return copy(self._fields)

    def has_fields(self):
        return self._fields is not None


class AddedBeforeMessage(ServerMessage):
    def __init__(self, collection, id_, before, fields=None):
        self._collection = collection
        self._id = id_
        self._before = before
        self._fields = copy(fields)

    def __eq__(self, other):
        return (self._collection == other._collection
                and self._id == other._id
                and self._before == other.before
                and self._fields == other._fields)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            'AddedBeforeMessage('
            'collection={!r}, '
            'id_={!r}, '
            'before={!r}, '
            'fields={!r})'
        ).format(
            self._collection,
            self._id,
            self._before,
            self._fields,
        )

    @property
    def collection(self):
        return self._collection

    @property
    def id_(self):
        return self._id

    @property
    def before(self):
        return self._before

    @property
    def fields(self):
        if not self.has_fields():
            raise AttributeError('added before message has no `fields` field')
        return copy(self._fields)

    def has_fields(self):
        return self._fields is not None


class ChangedMessage(ServerMessage):
    def __init__(self, collection, id_, cleared=None, fields=None):
        self._collection = collection
        self._id = id_
        self._cleared = copy(cleared)
        self._fields = copy(fields)

    def __eq__(self, other):
        return (self._collection == other._collection
                and self._id == other._id
                and self._cleared == other._cleared
                and self._fields == other._fields)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            'ChangedMessage('
            'collection={!r}, '
            'id_={!r}, '
            'cleared={!r}, '
            'fields={!r})'
        ).format(
            self._collection,
            self._id,
            self._cleared,
            self._fields,
        )

    @property
    def collection(self):
        return self._collection

    @property
    def id_(self):
        return self._id

    @property
    def cleared(self):
        if not self.has_cleared():
            raise AttributeError('changed message has no `cleared` field')
        return copy(self._cleared)

    @property
    def fields(self):
        if not self.has_fields():
            raise AttributeError('changed message has no `fields` field')
        return copy(self._fields)

    def has_cleared(self):
        return self._cleared is not None

    def has_fields(self):
        return self._fields is not None


class ConnectedMessage(ServerMessage):
    def __init__(self, session):
        self._session = session

    def __eq__(self, other):
        return self._session == other._session

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return 'ConnectedMessage(session={!r})'.format(self._session)

    @property
    def session(self):
        return self._session


class ErrorMessage(ServerMessage):
    def __init__(self, reason, offending_pod):
        self._reason = reason
        self._offending_pod = offending_pod

    def __eq__(self, other):
        return (self._reason == other._reason
                and self._offending_pod == other._offending_pod)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            'ErrorMessage('
            'reason={!r}, '
            'offending_pod={!r})'
        ).format(
            self._reason,
            self._offending_pod
        )

    @property
    def reason(self):
        return self._reason

    @property
    def offending_pod(self):
        return self._offending_pod


class FailedMessage(ServerMessage):
    def __init__(self, version):
        self._version = version

    def __eq__(self, other):
        return self._version == other._version

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return 'FailedMessage(version={!r})'.format(self._version)

    @property
    def version(self):
        return self._version


class MovedBeforeMessage(ServerMessage):
    def __init__(self, collection, id_, before):
        self._collection = collection
        self._id = id_
        self._before = before

    def __eq__(self, other):
        return (self._collection == other._collection
                and self._id == other._id
                and self._before == other._before)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            'MovedBeforeMessage('
            'collection={!r}, '
            'id_={!r}, '
            'before={!r})'
        ).format(
            self._collection,
            self._id,
            self._before
        )

    @property
    def collection(self):
        return self._collection

    @property
    def id_(self):
        return self._id

    @property
    def before(self):
        return self._before


class NosubMessage(ServerMessage):
    def __init__(self, id_, error=None):
        self._id = id_
        self._error = error

    def __eq__(self, other):
        return (self._id == other._id
                and self._error == other._error)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            'NosubMessage('
            'id_={!r}, '
            'error={!r})'
        ).format(
            self._id,
            self._error
        )

    @property
    def id_(self):
        return self._id

    @property
    def error(self):
        if not self.has_error():
            raise AttributeError('nosub message has no `error` field')
        return self._error

    def has_error(self):
        return self._error is not None


class ReadyMessage(ServerMessage):
    def __init__(self, subs):
        self._subs = copy(subs)

    def  __eq__(self, other):
        return self._subs == other._subs

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return 'ReadyMessage(subs={!r})'.format(self._subs)

    @property
    def subs(self):
        return copy(self._subs)


class RemovedMessage(ServerMessage):
    def __init__(self, collection, id_):
        self._collection = collection
        self._id = id_

    def __eq__(self, other):
        return (self._collection == other._collection
                and self._id == other._id)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            'RemovedMessage('
            'collection={!r}, '
            'id_={!r})'
        ).format(
            self._collection,
            self._id,
        )

    @property
    def collection(self):
        return self._collection

    @property
    def id_(self):
        return self._id


class ResultMessage(ServerMessage):
    def __init__(self, id_, error=None, result=None):
        super(ResultMessage, self).__init__()
        if nexists([error, result]) != 1:
            raise ValueError('either error or result must be given')
        self._id = id_
        self._error = error
        self._result = result

    def __eq__(self, other):
        return (self._id == other._id
                and self._error == other._error
                and self._result == other._result)

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return (
            'ResultMessage('
            'id_={!r}, '
            'error={!r}, '
            'result={!r})'
        ).format(
            self._id,
            self._error,
            self._result
        )

    @property
    def id_(self):
        return self._id

    @property
    def error(self):
        if not self.has_error():
            raise AttributeError('result message has no `error` field')
        return self._error

    @property
    def result(self):
        if not self.has_result():
            raise AttributeError('result message has not `result` field')
        return self._result

    def has_error(self):
        return self._error is not None

    def has_result(self):
        return self._result is not None


class UpdatedMessage(ServerMessage):
    def __init__(self, methods):
        super(UpdatedMessage, self).__init__()
        self._methods = copy(methods)

    def __eq__(self, other):
        return self._methods == other._methods

    def __ne__(self, other):
        return not self == other

    def __repr__(self):
        return str(self)

    def __str__(self):
        return 'UpdatedMessage(methods={!r})'.format(self._methods)

    @property
    def methods(self):
        return copy(self._methods)


# =============================================================================
# = Message constants                                                         =
# =============================================================================

# Client
MSG_CONNECT = 'connect'
MSG_METHOD  = 'method'
MSG_SUB     = 'sub'
MSG_UNSUB   = 'unsub'

# Server
MSG_ADDED        = 'added'
MSG_ADDED_BEFORE = 'addedBefore'
MSG_CHANGED      = 'changed'
MSG_CONNECTED    = 'connected'
MSG_ERROR        = 'error'
MSG_FAILED       = 'failed'
MSG_MOVED_BEFORE = 'movedBefore'
MSG_NOSUB        = 'nosub'
MSG_READY        = 'ready'
MSG_REMOVED      = 'removed'
MSG_RESULT       = 'result'
MSG_UPDATED      = 'updated'


# =============================================================================
# = Base message factories                                                    =
# =============================================================================

class AggregateFactory(object):
    def __init__(self, factory_classes, key):
        self._factories = {F.SRC_TYPE: F() for F in factory_classes}
        self._key = key

    def create(self, *args, **kwargs):
        key = self._key(*args, **kwargs)
        return self._factories[key].create(*args, **kwargs)


class AggregrateMessageFactory(object):
    def __init__(self, factory_classes):
        def key(pod):
            return pod['msg']
        self._factory = AggregateFactory(factory_classes, key)

    def create(self, pod):
        return self._factory.create(pod)


class AggregratePodMessageFactory(object):
    def __init__(self, factory_classes):
        self._factory = AggregateFactory(factory_classes, type)

    def create(self, message):
        return self._factory.create(message)


# =============================================================================
# = Client message factories                                                  =
# =============================================================================

# = connect messages factories ================================================

class ConnectMessageFactory(object):
    SRC_TYPE = MSG_CONNECT

    def create(self, pod):
        return ConnectMessage(
            pod['version'],
            session=pod.get('session'),
            support=pod.get('support'),
        )


class PodConnectMessageFactory(object):
    SRC_TYPE = ConnectMessage

    def create(self, message):
        pod = {
            'msg'    : MSG_CONNECT,
            'version': message.version,
        }
        if message.has_support():
            pod['support'] = message.support
        if message.has_session():
            pod['session'] = message.session
        return pod


# = method messages factories =================================================

class MethodMessageFactory(object):
    SRC_TYPE = MSG_METHOD

    def create(self, pod):
        return MethodMessage(
            pod['id'],
            pod['method'],
            pod['params'],
        )


class PodMethodMessageFactory(object):
    SRC_TYPE = MethodMessage

    def create(self, message):
        return {
            'msg'   : MSG_METHOD,
            'id'    : message.id_,
            'method': message.method,
            'params': message.params,
        }



# = sub message factories =====================================================

class SubMessageFactory(object):
    SRC_TYPE = MSG_SUB

    def create(self, pod):
        return SubMessage(
            pod['id'],
            pod['name'],
            params=pod.get('params'),
        )


class PodSubMessageFactory(object):
    SRC_TYPE = SubMessage

    def create(self, message):
        pod = {
            'msg' : MSG_SUB,
            'id'  : message.id_,
            'name': message.name
        }
        if message.has_params():
            pod['params'] = message.params
        return pod


# = unsub message factories ===================================================

class UnsubMessageFactory(object):
    SRC_TYPE = MSG_UNSUB

    def create(self, pod):
        return UnsubMessage(pod['id'])


class PodUnsubMessageFactory(object):
    SRC_TYPE = UnsubMessage

    def create(self, message):
        return {
            'msg': MSG_UNSUB,
            'id' : message.id_
        }


# = Aggregates factories ======================================================

class ClientMessageFactory(object):
    def __init__(self):
        factory_classes = [
            ConnectMessageFactory,
            MethodMessageFactory,
            SubMessageFactory,
            UnsubMessageFactory,
        ]
        self._factory = AggregrateMessageFactory(factory_classes)

    def create(self, message):
        return self._factory.create(message)


class PodClientMessageFactory(object):
    def __init__(self):
        factory_classes = [
            PodConnectMessageFactory,
            PodMethodMessageFactory,
            PodSubMessageFactory,
            PodUnsubMessageFactory,
        ]
        self._factory = AggregratePodMessageFactory(factory_classes)

    def create(self, message):
        return self._factory.create(message)


# =============================================================================
# = Server message factories                                                  =
# =============================================================================

# = added message factories ===================================================

class AddedMessageFactory(object):
    SRC_TYPE = MSG_ADDED

    def create(self, pod):
        return AddedMessage(
            pod['collection'],
            pod['id'],
            fields=pod.get('fields')
        )


class PodAddedMessageFactory(object):
    SRC_TYPE = AddedMessage

    def create(self, message):
        pod = {
            'msg'       : MSG_ADDED,
            'id'        : message.id_,
            'collection': message.collection,
        }
        if message.has_fields():
            pod['fields'] = message.fields
        return pod


# = addedBefore message factories =============================================

class AddedBeforeMessageFactory(object):
    SRC_TYPE = MSG_ADDED_BEFORE

    def create(self, pod):
        return AddedBeforeMessage(
            pod['collection'],
            pod['id'],
            pod['before'],
            pod.get('fields'),
        )


class PodAddedBeforeMessageFactory(object):
    SRC_TYPE = AddedBeforeMessage

    def create(self, message):
        pod = {
            'msg'       : MSG_ADDED_BEFORE,
            'collection': message.collection,
            'id'        : message.id_,
            'before'    : message.before,
        }
        if message.has_fields():
            pod['fields'] = message.fields
        return pod


# = changed message factories =================================================

class ChangedMessageFactory(object):
    SRC_TYPE = MSG_CHANGED

    def create(self, pod):
        return ChangedMessage(
            pod['collection'],
            pod['id'],
            cleared=pod.get('cleared'),
            fields=pod.get('fields'),
        )


class PodChangedMessageFactory(object):
    SRC_TYPE = ChangedMessage

    def create(self, message):
        pod = {
            'msg'       : MSG_CHANGED,
            'collection': message.collection,
            'id'        : message.id_,
        }
        if message.has_cleared():
            pod['cleared'] = message.cleared
        if message.has_fields():
            pod['fields'] = message.fields
        return pod


# = connected message factories ===============================================

class ConnectedMessageFactory(object):
    SRC_TYPE = MSG_CONNECTED

    def create(self, pod):
        return ConnectedMessage(pod['session'])


class PodConnectedMessageFactory(object):
    SRC_TYPE = ConnectedMessage

    def create(self, message):
        return {
            'msg'    : MSG_CONNECTED,
            'session': message.session,
        }


# = error message factories ===================================================

class ErrorMessageFactory(object):
    SRC_TYPE = MSG_ERROR

    def create(self, pod):
        return ErrorMessage(pod['reason'], pod['offendingMessage'])


class PodErrorMessageFactory(object):
    SRC_TYPE = ErrorMessage

    def create(self, message):
        return {
            'msg'             : MSG_ERROR,
            'reason'          : message.reason,
            'offendingMessage': message.offending_pod,
        }


# = failed message factories ==================================================

class FailedMessageFactory(object):
    SRC_TYPE = MSG_FAILED

    def create(self, pod):
        return FailedMessage(pod['version'])


class PodFailedMessageFactory(object):
    SRC_TYPE = FailedMessage

    def create(self, message):
        return {
            'msg'    : MSG_FAILED,
            'version': message.version,
        }


# = movedBefore message factories =============================================

class MovedBeforeMessageFactory(object):
    SRC_TYPE = MSG_MOVED_BEFORE

    def create(self, pod):
        return MovedBeforeMessage(
            pod['collection'],
            pod['id'],
            pod['before'],
        )


class PodMovedBeforeMessageFactory(object):
    SRC_TYPE = MovedBeforeMessage

    def create(self, message):
        return {
            'msg'       : MSG_MOVED_BEFORE,
            'collection': message.collection,
            'id'        : message.id_,
            'before'    : message.before,
        }


# = nosub message factories ===================================================

class NosubMessageFactory(object):
    SRC_TYPE = MSG_NOSUB

    def create(self, pod):
        return NosubMessage(pod['id'], pod.get('error'))


class PodNosubMessageFactory(object):
    SRC_TYPE = NosubMessage

    def create(self, message):
        pod = {
            'msg': MSG_NOSUB,
            'id' : message.id_,
        }
        if message.has_error():
            pod['error'] = message.error
        return pod


# = ready message factories ===================================================

class ReadyMessageFactory(object):
    SRC_TYPE = MSG_READY

    def create(self, pod):
        return ReadyMessage(pod['subs'])


class PodReadyMessageFactory(object):
    SRC_TYPE = ReadyMessage

    def create(self, message):
        return {'msg': MSG_READY, 'subs': message.subs}


# = remove message factories ==================================================

class RemoveMessageFactory(object):
    SRC_TYPE = MSG_REMOVED

    def create(self, pod):
        return RemovedMessage(
            pod['collection'],
            pod['id'],
        )


class PodRemovedMessageFactory(object):
    SRC_TYPE = RemovedMessage

    def create(self, message):
        return {
            'msg'       : MSG_REMOVED,
            'collection': message.collection,
            'id'        : message.id_,
        }


# = result message factories ==================================================

class ResultMessageFactory(object):
    SRC_TYPE = MSG_RESULT

    def create(self, pod):
        return ResultMessage(
            pod['id'],
            error=pod.get('error'),
            result=pod.get('result'),
        )


class PodResultMessageFactory(object):
    SRC_TYPE = ResultMessage

    def create(self, message):
        pod = {
            'msg': MSG_RESULT,
            'id' : message.id_,
        }
        if message.has_error():
            pod['error'] = message.error
        if message.has_result():
            pod['result'] = message.result
        return pod


# = updated message factories =================================================

class UpdatedMessageFactory(object):
    SRC_TYPE = MSG_UPDATED

    def create(self, pod):
        return UpdatedMessage(pod['methods'])


class PodUpdatedMessageFactory(object):
    SRC_TYPE = UpdatedMessage

    def create(self, message):
        return {
            'msg'    : MSG_UPDATED,
            'methods': message.methods,
        }


# = Aggregates factories ======================================================

class ServerMessageFactory(object):
    def __init__(self):
        factory_classes = [
            AddedMessageFactory,
            AddedBeforeMessageFactory,
            ConnectedMessageFactory,
            ChangedMessageFactory,
            ErrorMessageFactory,
            FailedMessageFactory,
            MovedBeforeMessageFactory,
            NosubMessageFactory,
            ReadyMessageFactory,
            RemoveMessageFactory,
            ResultMessageFactory,
            UpdatedMessageFactory,
        ]
        self._factory = AggregrateMessageFactory(factory_classes)

    def create(self, pod):
        return self._factory.create(pod)


class PodServerMessageFactroy(object):
    def __init__(self):
        factory_classes = [
            PodAddedMessageFactory,
            PodAddedBeforeMessageFactory,
            PodConnectedMessageFactory,
            PodChangedMessageFactory,
            PodErrorMessageFactory,
            PodFailedMessageFactory,
            PodMovedBeforeMessageFactory,
            PodNosubMessageFactory,
            PodReadyMessageFactory,
            PodRemovedMessageFactory,
            PodResultMessageFactory,
            PodUpdatedMessageFactory,
        ]
        self._factory = AggregratePodMessageFactory(factory_classes)

    def create(self, message):
        return self._factory.create(message)


# =============================================================================
# = Message filters                                                           =
# =============================================================================

class MessageFilter:
    pass


class PodClientMessageFilter(MessageFilter):
    def accept(self, pod):
        return True


class PodServerMessageFilter(MessageFilter):
    def accept(self, pod):
        return 'msg' in pod


# =============================================================================
# = Message parser/serializer                                                 =
# =============================================================================

class PodMessageParser(object):
    def parse(self, text):
        return json.loads(text)


class PodMessageSerializer(object):
    def serialize(self, pod):
        return json.dumps(pod)


# =============================================================================
# = Sockets                                                                   =
# =============================================================================

class _StrategyWebSocketClient(WebSocketClient):
    def __init__(
        self,
        url,
        opened_callback=None,
        closed_callback=None,
        received_message_callback=None,
    ):
        super(_StrategyWebSocketClient, self).__init__(url)
        self._closed_callback = closed_callback
        self._opened_callback = opened_callback
        self._received_message_callback = received_message_callback

    def opened(self):
        if self._opened_callback is not None:
            self._opened_callback()

    def received_message(self, message):
        if self._received_message_callback is not None:
            self._received_message_callback(message)

    def closed(self, code, reason=None):
        if self._closed_callback is not None:
            self._closed_callback(code, reason=reason)


class StrategyWebSocketClient(object):
    def __init__(self, *args, **kwargs):
        self._socket = _StrategyWebSocketClient(*args, **kwargs)

    def connect(self, *args, **kwargs):
        return self._socket.connect(*args, **kwargs)

    def send(self, *args, **kwargs):
        return self._socket.send(*args, **kwargs)

    def close(self, *args, **kwargs):
        return self._socket.close(*args, **kwargs)


class ManagedWebSocketClient(object):
    def __init__(self, socket):
        self._socket = socket

    def send(self, *args, **kwargs):
        return self._socket.send(*args, **kwargs)


@contextmanager
def WebSocketClientManager(socket):
    socket.connect()
    yield ManagedWebSocketClient(socket)
    socket.close()


class ServerUrl(object):
    def __init__(self, destination, scheme='ws', path='/websocket'):
        self._url = urlunparse((scheme, destination, path, '', '', ''))

    def __str__(self):
        return self._url


class MessageWebSocketClient(object):
    def __init__(
        self,
        url,
        opened_callback=None,
        received_message_callback=None,
        closed_callback=None,
    ):
        if received_message_callback is None:
            callback = None
        else:
            self._received_message_callback = received_message_callback
            callback = self._received_message

        self._socket = StrategyWebSocketClient(
            str(url),
            opened_callback=opened_callback,
            received_message_callback=callback,
            closed_callback=closed_callback,
        )

        self._parser = PodMessageParser()
        self._filter = PodServerMessageFilter()
        self._msgfactory = ServerMessageFactory()
        self._podfactory = PodClientMessageFactory()
        self._serializer = PodMessageSerializer()

    def _received_message(self, ws_message):
        text = ws_message.data
        pod = self._parser.parse(text)
        if self._filter.accept(pod):
            message = self._msgfactory.create(pod)
            self._received_message_callback(message)

    def connect(self):
        self._socket.connect()

    def send(self, message):
        pod = self._podfactory.create(message)
        text = self._serializer.serialize(pod)
        self._socket.send(text)

    def close(self):
        self._socket.close()


# =============================================================================
# = Connect                                                                   =
# =============================================================================

class DdpConnection(object):
    def __init__(
        self,
        url,
        connect_message,
        on_connected=None,
        on_disconnected=None,
        on_failed=None,
    ):
        super(DdpConnection, self).__init__()

        self._connect_message = connect_message

        self._socket = MessageWebSocketClient(
            url,
            opened_callback=self._opened,
            received_message_callback=self._received_message,
            closed_callback=closed_callback,
        )

    def _opened(self):
        msg = self._connect_message
        self._socket.send(msg)

    def _received_message(self, message):
        self._received_message_callback(message)

    def connect(self):
        self._socket.connect()

    def send(self, message):
        self._socket.send(message)

    def close(self):
        self._socket.close()



# =============================================================================
# = Future                                                                    =
# =============================================================================

class Timeout(object):
    def __init__(self, duration)
        super(Timeout, self).__init__()
        self._duration = duration
        self._started = None

    def _now(self):
        return time.time()

    def start(self):
        self._started = self._now()

    def remaining(self):
        elapsed = self._now() - self._started
        remaining = self._duration - elapsed
        if remaining < 0
            remaining = 0
        return remaining


class Future(object):
    def __init__(self):
        self._cond = threading.Condition()
        self._value = None
        self._is_set = False

    def get(self, timeout=None):
        with self._cond:
            while not self._is_set:
                self._cond.wait(timeout=timeout)
        return self._value

    def set(self, value):
        with self._cond:
            self._value = value
            self._is_set = True


