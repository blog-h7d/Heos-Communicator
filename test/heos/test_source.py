from heos.sources import HeosSearchCriteria, HeosSource


def test_init_search_criteria():
    data = {
        "scid": "scid1",
        "name": "Name of Criteria",
        "wildcard": "yes",
    }

    sc = HeosSearchCriteria("192.168.1.1", None, data)
    assert sc._ip == "192.168.1.1"
    assert not sc._parent
    assert sc.scid == "scid1"
    assert sc.name == "Name of Criteria"
    assert sc.allow_wildcard
    assert not sc.is_playable
    assert sc.cid == 0


def test_init_search_criteria2():
    ip = "192.168.1.1"

    data = {
        "scid": "scid2",
        "name": "Name of Criteria",
        "wildcard": "no",
        "playable": "yes",
        "cid": "test123"
    }

    source_data = {
        "name": "source name",
        "image_url": "source logo url",
        "type": "source type",
        "sid": 17,
        "available": "true/false",
        "service_username": "user name of the service account"
    }

    source = HeosSource(ip, None, source_data)
    sc = HeosSearchCriteria(ip, source, data)
    assert sc._ip == ip
    assert sc._parent == source
    assert sc.scid == "scid2"
    assert sc.name == "Name of Criteria"
    assert not sc.allow_wildcard
    assert sc.is_playable
    assert sc.cid == "test123"
