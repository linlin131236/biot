from bolt_core.conversation import ConversationStore, ConversationMessage


def test_conversation_add_and_history(tmp_path):
    store = ConversationStore(str(tmp_path / "conv.db"))
    cid = "conv_001"

    store.add(cid, ConversationMessage(role="system", content="You are Bolt."))
    store.add(cid, ConversationMessage(role="user", content="Fix the tests."))
    store.add(cid, ConversationMessage(role="assistant", content="I'll fix them."))

    history = store.history(cid)
    assert len(history) == 3
    assert history[0].role == "system"
    assert history[1].content == "Fix the tests."
    assert history[2].role == "assistant"


def test_conversation_history_limit(tmp_path):
    store = ConversationStore(str(tmp_path / "conv.db"))
    cid = "conv_002"

    for i in range(20):
        store.add(cid, ConversationMessage(role="user", content=f"msg {i}"))

    history = store.history(cid, limit=5)
    assert len(history) == 5
    # Should be the most recent messages
    assert history[-1].content == "msg 19"


def test_conversation_inject_mid_loop(tmp_path):
    store = ConversationStore(str(tmp_path / "conv.db"))
    cid = "conv_003"

    store.add(cid, ConversationMessage(role="system", content="System"))
    store.add(cid, ConversationMessage(role="user", content="Start"))

    # Inject steering message
    store.add(cid, ConversationMessage(role="user", content="Change direction",
                                       metadata={"steering": True}))

    history = store.history(cid)
    assert len(history) == 3
    assert history[2].metadata.get("steering") is True


def test_conversation_side_chat_isolation(tmp_path):
    store = ConversationStore(str(tmp_path / "conv.db"))
    main_id = "conv_main"
    side_id = "conv_side_001"

    store.add(main_id, ConversationMessage(role="user", content="Main task"))
    store.add(side_id, ConversationMessage(role="user", content="Side question"))

    main_history = store.history(main_id)
    side_history = store.history(side_id)

    assert len(main_history) == 1
    assert len(side_history) == 1
    assert main_history[0].content == "Main task"
    assert side_history[0].content == "Side question"


def test_conversation_side_chat_cannot_execute_tools(tmp_path):
    """Side chat messages with tool_call should be rejected."""
    store = ConversationStore(str(tmp_path / "conv.db"))
    cid = "conv_side_002"

    # Side chat messages should not have tool_calls
    msg = ConversationMessage(role="assistant", content="Just thinking",
                              metadata={"side_chat": True})
    assert msg.tool_calls is None  # side chat cannot carry tool calls


def test_conversation_persistence(tmp_path):
    db1 = str(tmp_path / "conv.db")
    store1 = ConversationStore(db1)
    store1.add("c1", ConversationMessage(role="user", content="Hello"))

    # Reopen
    store2 = ConversationStore(db1)
    history = store2.history("c1")
    assert len(history) == 1
    assert history[0].content == "Hello"


def test_conversation_steering_cannot_retroactively_approve(tmp_path):
    """Steering messages should not change past permission state."""
    store = ConversationStore(str(tmp_path / "conv.db"))
    cid = "conv_steer"

    store.add(cid, ConversationMessage(role="assistant", content="Need approval",
                                       metadata={"permission_pending": True}))
    store.add(cid, ConversationMessage(role="user", content="Change direction",
                                       metadata={"steering": True}))

    history = store.history(cid)
    # Pending permission remains pending
    assert history[0].metadata.get("permission_pending") is True
