# Authorship and collaboration

This project is owned and directed by **Miguel Jackson**.

Milestones M0 through M3 were designed and implemented collaboratively from
Miguel's requirements by **OpenAI Codex using the GPT-5.6 Sol model**. Miguel
specified the project goals, approved the implementation plan, selected Python
as the integration language, and required the educational, security, and
domain-API design emphasis. Codex performed the repository analysis,
implementation, documentation, generic-client verification, and Claude Desktop
interoperability check under that direction. M3 added the OAuth-protected
Streamable HTTP application boundary and verified remote resource limits.

Codex is credited as an AI development collaborator, not as a legal author,
copyright holder, repository account, or independent maintainer.

The repository hero image was generated with OpenAI image generation through
Codex under Miguel's direction.

Development now continues with **Claude Code using Claude Opus 5.5**
(`claude-opus-5-5`) under Miguel's direction. Claude Code scoped the project to
the `vle` library alone, reviewed the `vle-thermo` 0.18 public API, and
implemented and tested the tool catalogue. Verification evidence is the test
suite (`tests/test_catalogue.py`). A material limitation is that tools run
synchronously, so the remote request timeout cannot interrupt a solve (see
`docs/architecture.md`). Claude Code is credited on the same terms as Codex: an
AI development collaborator, not a legal author or maintainer.

Future milestone records should name the human director, implementation agent,
exact model identifier, verification evidence, and material limitations.
