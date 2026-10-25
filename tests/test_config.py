from app.config import get_config


def test_example_config_is_valid(config_file):
    config = get_config()
    assert config.auth.jwt.ttl_hours == 24
    assert config.auth.invited.mail == ["mail1@xyz.com", "mail2@xyz.com"]
    assert config.auth.invited.instagram == ["instagram_handle1", "instagram_handle2"]


def test_edits_apply_without_restart(edit_config):
    assert not get_config().is_invited_email("new@person.org")
    edit_config(lambda d: d["auth"]["invited"]["mail"].append("New@Person.org"))
    assert get_config().is_invited_email("new@person.org")
    edit_config(lambda d: d["ttl"].update(ongoing_hours=5))
    assert get_config().ttl.ongoing_hours == 5


def test_invalid_file_keeps_last_valid_version(config_file):
    good = get_config()
    config_file.write_text("auth: [this is: not valid", encoding="utf-8")
    assert get_config().auth.invited.mail == good.auth.invited.mail


def test_config_errors_never_echo_values(edit_config, capsys):
    get_config()
    edit_config(lambda d: d["auth"]["google"].update(unknown_key="TOP-SECRET-VALUE"))
    get_config()
    err = capsys.readouterr().err
    assert "auth.google.unknown_key" in err and "TOP-SECRET-VALUE" not in err


def test_instagram_invites_ignore_at_and_case(config_file):
    assert get_config().is_invited_instagram("@Instagram_Handle1")
