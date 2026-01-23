"""
Module quản lý kết nối MongoDB tập trung cho toàn bộ ứng dụng.
Tự động tìm PRIMARY node trong replica set.
"""
from pymongo import MongoClient
from pymongo.errors import NotPrimaryError, ServerSelectionTimeoutError
from decouple import config
import time
from contextlib import contextmanager
from pymongo.read_concern import ReadConcern
from pymongo.write_concern import WriteConcern
from pymongo.read_preferences import ReadPreference

REPLICA_SET_PORTS = [27108, 27109, 27110]


def find_primary_port():
    """Tìm port của PRIMARY node trong replica set"""
    for port in REPLICA_SET_PORTS:
        try:
            uri = f"mongodb://localhost:{port}/Login?directConnection=true"
            client = MongoClient(uri, serverSelectionTimeoutMS=3000)
            result = client.admin.command('hello')
            if result.get('isWritablePrimary', False) or result.get('ismaster', False):
                client.close()
                print(f"Found PRIMARY at port {port}")
                return port
            client.close()
        except Exception:
            continue
    return None


class MongoDBConnection:
    _instance = None
    _client = None
    _db = None
    _current_port = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def reset_connection(cls):
        """Reset connection để tìm PRIMARY mới"""
        if cls._client:
            try:
                cls._client.close()
            except:
                pass
        cls._client = None
        cls._db = None
        cls._current_port = None

    @classmethod
    def get_client(cls, max_retries=5, retry_delay=3):
        """Lấy MongoDB client với auto-discovery PRIMARY"""
        if cls._client is not None:
            try:
                cls._client.admin.command('ping')
                return cls._client
            except (NotPrimaryError, ServerSelectionTimeoutError):
                print("Connection lost or node is no longer PRIMARY. Reconnecting...")
                cls.reset_connection()

        for attempt in range(max_retries):
            try:
                mongo_uri = config("MONGO_URI")
                
                try:
                    cls._client = MongoClient(
                        mongo_uri,
                        serverSelectionTimeoutMS=5000,
                        connectTimeoutMS=5000,
                        socketTimeoutMS=20000,
                        retryWrites=True,
                        w="majority"
                    )
                    cls._client.admin.command('hello')
                    result = cls._client.admin.command('hello')
                    if not (result.get('isWritablePrimary', False) or result.get('ismaster', False)):
                        raise NotPrimaryError("Connected node is not PRIMARY")
                except (NotPrimaryError, ServerSelectionTimeoutError):
                    print("Configured URI is not PRIMARY. Auto-discovering PRIMARY...")
                    primary_port = find_primary_port()
                    if primary_port:
                        mongo_uri = f"mongodb://localhost:{primary_port}/Login?directConnection=true"
                        cls._client = MongoClient(
                            mongo_uri,
                            serverSelectionTimeoutMS=5000,
                            connectTimeoutMS=5000,
                            socketTimeoutMS=20000,
                            retryWrites=True,
                            w="majority"
                        )
                        cls._current_port = primary_port
                    else:
                        raise Exception("Could not find PRIMARY node in replica set")
                
                cls._client.admin.command('ping')
                print("MongoDB connection established successfully!")
                return cls._client
                
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"MongoDB connection attempt {attempt + 1}/{max_retries} failed: {e}")
                    print(f"Retrying in {retry_delay} seconds...")
                    time.sleep(retry_delay)
                else:
                    print(f"Failed to connect to MongoDB after {max_retries} attempts")
                    raise e

    @classmethod
    def get_database(cls):
        """Lấy database instance"""
        if cls._db is None:
            client = cls.get_client()
            cls._db = client[config("DB_NAME")]
        return cls._db

    @classmethod
    def create_index_safe(cls, collection, keys, **kwargs):
        """Tạo index với retry logic và error handling"""
        max_retries = 3
        retry_delay = 2

        for attempt in range(max_retries):
            try:
                collection.create_index(keys, **kwargs)
                return True
            except NotPrimaryError:
                cls.reset_connection()
                if attempt < max_retries - 1:
                    time.sleep(retry_delay)
            except Exception as e:
                error_msg = str(e)
                if "already exists" in error_msg.lower():
                    return True
                if attempt < max_retries - 1:
                    print(f"Index creation attempt {attempt + 1} failed: {e}")
                    time.sleep(retry_delay)
                else:
                    print(f"Warning: Could not create index after {max_retries} attempts: {e}")
                    return False
        return False
    @classmethod
    def start_session(cls):
        client = cls.get_client()
        return client.start_session()

    @classmethod
    @contextmanager
    def transaction(cls):
        """
        Transaction chuẩn:
        - majority write concern
        - snapshot read concern
        - primary read
        """
        with cls.start_session() as session:
            try:
                session.start_transaction(
                    read_concern=ReadConcern("snapshot"),
                    write_concern=WriteConcern("majority", wtimeout=5000),
                    read_preference=ReadPreference.PRIMARY
                )
                yield session
                session.commit_transaction()
            except (NotPrimaryError, ServerSelectionTimeoutError):
                # PRIMARY đổi / mất kết nối -> rollback + reset để lần sau reconnect
                try:
                    session.abort_transaction()
                except:
                    pass
                cls.reset_connection()
                raise
            except Exception:
                try:
                    session.abort_transaction()
                except:
                    pass
                raise

    @classmethod
    def run_in_transaction(cls, fn, *args, **kwargs):
        """
        Gọi hàm fn trong transaction.
        fn PHẢI nhận param session=...
        """
        with cls.transaction() as session:
            return fn(*args, session=session, **kwargs)


# Singleton instances
def get_mongo_client():
    return MongoDBConnection.get_client()


def get_database():
    return MongoDBConnection.get_database()

def create_index_safe(collection, keys, **kwargs):
    return MongoDBConnection.create_index_safe(collection, keys, **kwargs)

def start_session():
    return MongoDBConnection.start_session()

def transaction():
    return MongoDBConnection.transaction()

def run_in_transaction(fn, *args, **kwargs):
    return MongoDBConnection.run_in_transaction(fn, *args, **kwargs)
