from airport_twin.journey import Policy, simulate, wait_seconds


def test_queue_and_deadline_edges():
    assert wait_seconds([5, 8, 2], 2) == 7
    fixed = Policy(walk=(60, 60, 60), standard=(10, 10, 10))
    for budget, expected in ((70, 1), (69, 0), (-1, 0)):
        _, profiles = simulate(0, budget, 4, 3, fixed)
        profile = profiles[0]
        assert profile["arms"][0]["probability"] == expected
        assert profile["arms"][0]["sample"] == {"security_wait": 0, "screening": 10, "walk": 60}


def test_paired_profiles_and_replay():
    args = (67, 1400, 42, 100, Policy())
    rows, profiles = simulate(*args)
    assert (rows, profiles) == simulate(*args)
    assert len(rows) == 400 and len(profiles) == 16
    for base, extra in zip(rows[::2], rows[1::2], strict=True):
        assert extra[4] <= base[4]
        assert base[5:] == extra[5:]
    for p in profiles:
        assert p["gain"] >= 0
        assert sum(p["arms"][0]["bins"]) == 100
        assert p["arms"][0]["sample"]["security_wait"] >= 0
    assert profiles[0]["ahead"] + profiles[8]["ahead"] == 67
