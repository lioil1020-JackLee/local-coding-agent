# Project Structure

  ├── .gitignore  
  ├── README.md  
  ├── agent_runtime  
  │   ├── git_debug.log  
  │   ├── logs  
  │   ├── mcp_server.log  
  │   ├── sessions  
  │   └── snapshots  
  ├── continue  
  │   ├── config.yaml  
  │   ├── rules  
  │   │   ├── builder-tooling.md  
  │   │   ├── chinese-style.md  
  │   │   └── safe-editing.md  
  │   └── system-prompts  
  │       ├── builder.md  
  │       ├── editor.md  
  │       ├── planner.md  
  │       ├── reviewer.md  
  │       └── summarizer.md  
  ├── docs  
  │   ├── 00_文件導航.md  
  │   ├── 01_目標與方向.md  
  │   ├── 02_設計方案.md  
  │   ├── 03_pipeline架構.md  
  │   ├── 04_ExecutionController說明.md  
  │   ├── 05_工作流程與Continue.md  
  │   ├── 06_合作與貢獻.md  
  │   ├── 07_CONTRIBUTING.md  
  │   ├── 08_CHANGELOG.md  
  │   ├── 09_變更與進度.md  
  │   └── 10_AGENT_PROGRESS.md  
  ├── pyproject.toml  
  ├── repo_guardian_agent  
  │   ├── __init__.py                                  8 lines  
  │   ├── patch_generator.py                          44 lines  
  │   ├── planner.py                                  67 lines  
  │   └── validation_controller.py                   120 lines  
  ├── repo_guardian_mcp  
  │   ├── __init__.py                                  5 lines  
  │   ├── agent_loop.py                              129 lines  
  │   ├── cli.py                                     187 lines  
  │   ├── cli_chat_service.py                         38 lines  
  │   ├── models.py                                  298 lines  
  │   ├── prompts  
  │   │   ├── patch_generation.txt  
  │   │   └── validation_summary.txt  
  │   ├── server.py                                  251 lines  
  │   ├── services  
  │   │   ├── __init__.py                              5 lines  
  │   │   ├── agent_planner.py                       261 lines  
  │   │   ├── agent_session_runtime.py               184 lines  
  │   │   ├── agent_session_state_service.py          71 lines  
  │   │   ├── cli_agent_service.py                    70 lines  
  │   │   ├── cli_chat_service.py                    203 lines  
  │   │   ├── conversation_orchestrator.py           269 lines  
  │   │   ├── diff_service.py                        179 lines  
  │   │   ├── edit_execution_orchestrator.py         529 lines  
  │   │   ├── entrypoint_service.py                   29 lines  
  │   │   ├── execution_controller.py                734 lines  
  │   │   ├── git_session_maintenance_service.py     138 lines  
  │   │   ├── intent_resolution_service.py            53 lines  
  │   │   ├── patch_service.py                       299 lines  
  │   │   ├── planning_service.py                     69 lines  
  │   │   ├── planning_service_v2.py                  75 lines  
  │   │   ├── repo_scan_service.py                   152 lines  
  │   │   ├── report_service.py                        2 lines  
  │   │   ├── rollback_service.py                     98 lines  
  │   │   ├── runtime_plan_service.py                 49 lines  
  │   │   ├── sandbox_edit_service.py                108 lines  
  │   │   ├── sandbox_service.py                     179 lines  
  │   │   ├── session_cleanup_service.py             325 lines  
  │   │   ├── session_lifecycle_coordinator.py        76 lines  
  │   │   ├── session_service.py                      58 lines  
  │   │   ├── session_update_service.py               52 lines  
  │   │   ├── skill_graph_service.py                  19 lines  
  │   │   ├── staging_service.py                      86 lines  
  │   │   ├── symbol_service.py                       86 lines  
  │   │   ├── task_orchestrator.py                   118 lines  
  │   │   ├── validation_hook_service.py             144 lines  
  │   │   └── validation_service.py                  127 lines  
  │   ├── settings.py                                 53 lines  
  │   ├── skills.py                                  672 lines  
  │   ├── tool_registry.py                            48 lines  
  │   ├── tools  
  │   │   ├── __init__.py                             18 lines  
  │   │   ├── analyze_repo.py                         56 lines  
  │   │   ├── apply_to_workspace.py                   84 lines  
  │   │   ├── cleanup_sandbox.py                      35 lines  
  │   │   ├── cleanup_sessions.py                     39 lines  
  │   │   ├── create_task_session.py                 116 lines  
  │   │   ├── detect_project_commands.py               2 lines  
  │   │   ├── export_change_report.py                  2 lines  
  │   │   ├── find_entrypoints.py                     35 lines  
  │   │   ├── get_session_status.py                   42 lines  
  │   │   ├── get_session_workspace.py                19 lines  
  │   │   ├── git_status_plus.py                       2 lines  
  │   │   ├── impact_analysis.py                      11 lines  
  │   │   ├── list_sessions.py                        34 lines  
  │   │   ├── move_file.py                            74 lines  
  │   │   ├── pin_session.py                          17 lines  
  │   │   ├── plan_change.py                          53 lines  
  │   │   ├── preview_diff.py                         56 lines  
  │   │   ├── preview_session_diff.py                110 lines  
  │   │   ├── propose_patch.py                        83 lines  
  │   │   ├── read_code_region.py                     38 lines  
  │   │   ├── repo_overview.py                        63 lines  
  │   │   ├── resume_session.py                       47 lines  
  │   │   ├── rollback_session.py                     54 lines  
  │   │   ├── run_task_pipeline.py                    98 lines  
  │   │   ├── run_validation_pipeline.py             140 lines  
  │   │   ├── search_code.py                          26 lines  
  │   │   ├── semantic_guard.py                        2 lines  
  │   │   ├── stage_patch.py                          50 lines  
  │   │   ├── structured_edit.py                      53 lines  
  │   │   └── symbol_index.py                         11 lines  
  │   └── utils  
  │       ├── __init__.py                              7 lines  
  │       ├── command_utils.py                        26 lines  
  │       ├── file_utils.py                           43 lines  
  │       ├── git_utils.py                           166 lines  
  │       ├── json_utils.py                           27 lines  
  │       ├── paths.py                                78 lines  
  │       └── text_guard.py                           18 lines  
  └── tests  
      ├── test_agent_loop_trace.py                   102 lines  
      ├── test_agent_loop_v1.py                       20 lines  
      ├── test_agent_session_runtime.py               43 lines  
      ├── test_analysis_tools.py                      37 lines  
      ├── test_analyze_narrative_summary.py           25 lines  
      ├── test_chat_mode_v2.py                        79 lines  
      ├── test_cli_agent_service.py                   58 lines  
      ├── test_cli_agent_trace.py                     16 lines  
      ├── test_cli_chat_mode.py                       23 lines  
      ├── test_cli_diff_unicode_hotfix.py             24 lines  
      ├── test_cli_entrypoint.py                      62 lines  
      ├── test_execution_controller.py                97 lines  
      ├── test_execution_controller_compat.py         29 lines  
      ├── test_execution_controller_v1.py            234 lines  
      ├── test_get_session_status.py                  39 lines  
      ├── test_patch_service.py                       83 lines  
      ├── test_repo_overview.py                        4 lines  
      ├── test_rollback_session.py                    34 lines  
      ├── test_run_task_pipeline.py                  112 lines  
      ├── test_session_cleanup_service.py            117 lines  
      ├── test_session_git_cleanup.py                 85 lines  
      ├── test_session_lifecycle_coordinator.py       56 lines  
      ├── test_session_lifecycle_tools.py             63 lines  
      ├── test_skill_registry_v3.py                   52 lines  
      ├── test_text_guard.py                           4 lines  
      ├── test_validation_pipeline.py                 27 lines  
      └── test_validation_service.py                   4 lines  
