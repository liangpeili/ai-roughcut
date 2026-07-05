from ai_roughcut.cli import build_parser


def test_cli_uses_ai_flag_for_model_decisions():
    parser = build_parser()
    args = parser.parse_args(["input/interview_001.mp4", "--ai"])

    assert args.ai is True
