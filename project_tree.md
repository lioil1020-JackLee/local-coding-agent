# Project Structure

  ├── .gitignore  
  ├── .uv-cache  
  │   ├── .gitignore  
  │   ├── .lock  
  │   ├── CACHEDIR.TAG  
  │   ├── builds-v0  
  │   ├── interpreter-v4  
  │   │   └── e44bd5d36e7a95cd  
  │   │       └── 2d575ea63d1cfc9a.msgpack  
  │   ├── sdists-v9  
  │   │   ├── .gitignore  
  │   │   └── editable  
  │   │       └── 6c800c2e1daa644b  
  │   │           ├── .lock  
  │   │           ├── 7wOcJoGL46KQBqt03h8hA  
  │   │           ├── revision.rev  
  │   │           └── zISp5XZCd5BXbvbGX4QRo  
  │   └── simple-v20  
  │       └── pypi  
  │           ├── setuptools.lock  
  │           └── wheel.lock  
  ├── README.md  
  ├── agent_runtime  
  │   └── mcp_server.log  
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
  │   ├── 01_架構總覽與導讀.md  
  │   ├── 02_產品定位與設計原則.md  
  │   ├── 03_執行架構與技術主線.md  
  │   ├── 04_開發流程_協作與進度.md  
  │   └── 05_安裝流程說明.md  
  ├── pyproject.toml  
  ├── repo_guardian_agent  
  │   ├── __init__.py                                       8 lines  
  │   ├── patch_generator.py                               44 lines  
  │   ├── planner.py                                       67 lines  
  │   └── validation_controller.py                        120 lines  
  ├── repo_guardian_mcp  
  │   ├── __init__.py                                       5 lines  
  │   ├── agent_loop.py                                   129 lines  
  │   ├── cli.py                                          905 lines  
  │   ├── models.py                                       298 lines  
  │   ├── prompts  
  │   │   ├── patch_generation.txt  
  │   │   └── validation_summary.txt  
  │   ├── server.py                                       317 lines  
  │   ├── services  
  │   │   ├── __init__.py                                   5 lines  
  │   │   ├── agent_planner.py                            261 lines  
  │   │   ├── agent_session_runtime.py                    313 lines  
  │   │   ├── agent_session_state_service.py               71 lines  
  │   │   ├── benchmark_service.py                        262 lines  
  │   │   ├── cli_agent_service.py                        190 lines  
  │   │   ├── cli_chat_service.py                         194 lines  
  │   │   ├── continue_config_service.py                  723 lines  
  │   │   ├── continue_e2e_service.py                     136 lines  
  │   │   ├── conversation_orchestrator.py                269 lines  
  │   │   ├── diff_service.py                             179 lines  
  │   │   ├── edit_execution_orchestrator.py              562 lines  
  │   │   ├── entrypoint_service.py                        29 lines  
  │   │   ├── error_diagnosis_service.py                   92 lines  
  │   │   ├── execution_controller.py                     734 lines  
  │   │   ├── execution_flow_orchestrator.py               59 lines  
  │   │   ├── git_session_maintenance_service.py          138 lines  
  │   │   ├── health_report_service.py                    226 lines  
  │   │   ├── ide_bridge_service.py                       496 lines  
  │   │   ├── intent_resolution_service.py                 62 lines  
  │   │   ├── ops_service.py                              221 lines  
  │   │   ├── patch_service.py                            299 lines  
  │   │   ├── pipeline_background_service.py              130 lines  
  │   │   ├── plain_language_understanding_service.py      97 lines  
  │   │   ├── planning_service.py                         143 lines  
  │   │   ├── repo_scan_service.py                        203 lines  
  │   │   ├── report_service.py                             2 lines  
  │   │   ├── response_envelope_service.py                104 lines  
  │   │   ├── response_quality_gate_service.py            106 lines  
  │   │   ├── rollback_service.py                          98 lines  
  │   │   ├── routing_observability_service.py             64 lines  
  │   │   ├── runtime_cleanup_service.py                  289 lines  
  │   │   ├── runtime_plan_service.py                      49 lines  
  │   │   ├── safe_edit_guard_service.py                   72 lines  
  │   │   ├── sandbox_edit_service.py                     117 lines  
  │   │   ├── sandbox_service.py                          218 lines  
  │   │   ├── session_cleanup_service.py                  325 lines  
  │   │   ├── session_lifecycle_contract_service.py        78 lines  
  │   │   ├── session_lifecycle_coordinator.py             76 lines  
  │   │   ├── session_service.py                           58 lines  
  │   │   ├── session_update_service.py                    52 lines  
  │   │   ├── skill_graph_service.py                       19 lines  
  │   │   ├── staging_service.py                           86 lines  
  │   │   ├── symbol_service.py                            86 lines  
  │   │   ├── task_orchestrator.py                        100 lines  
  │   │   ├── task_state_machine.py                        54 lines  
  │   │   ├── trace_schema_service.py                      35 lines  
  │   │   ├── trace_summary_service.py                    279 lines  
  │   │   ├── truthfulness_guard_service.py               111 lines  
  │   │   ├── user_friendly_summary_service.py             88 lines  
  │   │   ├── user_preference_memory_service.py            96 lines  
  │   │   ├── validation_hook_service.py                  144 lines  
  │   │   └── validation_service.py                       127 lines  
  │   ├── settings.py                                      53 lines  
  │   ├── skills.py                                       737 lines  
  │   ├── tool_registry.py                                 62 lines  
  │   ├── tools  
  │   │   ├── __init__.py                                  18 lines  
  │   │   ├── analyze_repo.py                             214 lines  
  │   │   ├── apply_to_workspace.py                        84 lines  
  │   │   ├── cleanup_sandbox.py                           35 lines  
  │   │   ├── cleanup_sessions.py                          39 lines  
  │   │   ├── create_task_session.py                      116 lines  
  │   │   ├── detect_project_commands.py                    2 lines  
  │   │   ├── export_change_report.py                       2 lines  
  │   │   ├── find_entrypoints.py                          35 lines  
  │   │   ├── get_session_status.py                        42 lines  
  │   │   ├── get_session_workspace.py                     19 lines  
  │   │   ├── git_status_plus.py                            2 lines  
  │   │   ├── impact_analysis.py                           11 lines  
  │   │   ├── list_sessions.py                             34 lines  
  │   │   ├── move_file.py                                 74 lines  
  │   │   ├── pin_session.py                               17 lines  
  │   │   ├── pipeline_job_status.py                       13 lines  
  │   │   ├── plan_change.py                               53 lines  
  │   │   ├── preview_diff.py                              56 lines  
  │   │   ├── preview_session_diff.py                     110 lines  
  │   │   ├── propose_patch.py                             83 lines  
  │   │   ├── read_code_region.py                          38 lines  
  │   │   ├── repo_overview.py                             63 lines  
  │   │   ├── resume_session.py                            47 lines  
  │   │   ├── rollback_session.py                          54 lines  
  │   │   ├── run_task_pipeline.py                        500 lines  
  │   │   ├── run_validation_pipeline.py                  149 lines  
  │   │   ├── search_code.py                               26 lines  
  │   │   ├── semantic_guard.py                             2 lines  
  │   │   ├── stage_patch.py                               50 lines  
  │   │   ├── structured_edit.py                           53 lines  
  │   │   ├── symbol_index.py                              11 lines  
  │   │   └── workflow_gateway.py                         182 lines  
  │   ├── utils  
  │   │   ├── __init__.py                                   7 lines  
  │   │   ├── command_utils.py                             26 lines  
  │   │   ├── file_utils.py                                43 lines  
  │   │   ├── git_utils.py                                166 lines  
  │   │   ├── json_utils.py                                27 lines  
  │   │   ├── paths.py                                     78 lines  
  │   │   └── text_guard.py                                18 lines  
  │   └── workers  
  │       └── pipeline_background_worker.py                54 lines  
  ├── requirements.txt  
  └── tests  
      ├── conftest.py                                      29 lines  
      ├── test_agent_loop_trace.py                        102 lines  
      ├── test_agent_loop_v1.py                            20 lines  
      ├── test_agent_session_runtime.py                    77 lines  
      ├── test_analysis_tools.py                           74 lines  
      ├── test_analyze_narrative_summary.py                25 lines  
      ├── test_benchmark_cli.py                            66 lines  
      ├── test_chat_mode_v2.py                             79 lines  
      ├── test_cli_agent_service.py                        73 lines  
      ├── test_cli_agent_trace.py                          21 lines  
      ├── test_cli_chat_mode.py                            51 lines  
      ├── test_cli_diff_unicode_hotfix.py                  24 lines  
      ├── test_cli_entrypoint.py                          294 lines  
      ├── test_cli_json_output_hotfix.py                   28 lines  
      ├── test_cli_trace_canonical_regression.py           38 lines  
      ├── test_continue_config_service.py                 342 lines  
      ├── test_continue_e2e_service.py                     14 lines  
      ├── test_error_diagnosis_service.py                  19 lines  
      ├── test_execution_controller.py                     97 lines  
      ├── test_execution_controller_compat.py              29 lines  
      ├── test_execution_controller_v1.py                 234 lines  
      ├── test_get_session_status.py                       39 lines  
      ├── test_health_report_service.py                    38 lines  
      ├── test_ide_bridge_cli.py                          116 lines  
      ├── test_mcp_server_protocol.py                      60 lines  
      ├── test_observe_cli.py                              19 lines  
      ├── test_ops_service.py                              72 lines  
      ├── test_patch_service.py                            83 lines  
      ├── test_pipeline_background_service.py              42 lines  
      ├── test_plain_language_understanding.py             27 lines  
      ├── test_repo_overview.py                             4 lines  
      ├── test_response_envelope.py                        41 lines  
      ├── test_response_quality_gate_service.py            30 lines  
      ├── test_rollback_session.py                         34 lines  
      ├── test_run_task_pipeline.py                       112 lines  
      ├── test_run_task_pipeline_autodecompose.py         198 lines  
      ├── test_runtime_cleanup_service.py                 117 lines  
      ├── test_safe_edit_guard_service.py                  61 lines  
      ├── test_sandbox_service.py                          20 lines  
      ├── test_session_cleanup_service.py                 117 lines  
      ├── test_session_git_cleanup.py                      85 lines  
      ├── test_session_lifecycle_contract_service.py       26 lines  
      ├── test_session_lifecycle_coordinator.py            56 lines  
      ├── test_session_lifecycle_tools.py                  63 lines  
      ├── test_skill_registry_v3.py                        88 lines  
      ├── test_task_orchestrator_boundary.py               31 lines  
      ├── test_task_state_machine.py                       20 lines  
      ├── test_text_guard.py                                4 lines  
      ├── test_tool_registry_aliases.py                    17 lines  
      ├── test_trace_summary_canonical_force.py            28 lines  
      ├── test_trace_summary_canonical_regression.py       34 lines  
      ├── test_trace_summary_service.py                    89 lines  
      ├── test_trace_text_integration.py                   36 lines  
      ├── test_trace_text_single_source_hotfix.py          41 lines  
      ├── test_truthfulness_guard_service.py               30 lines  
      ├── test_user_preference_memory_service.py           33 lines  
      ├── test_validation_auto_rollback.py                 31 lines  
      ├── test_validation_pipeline.py                      27 lines  
      ├── test_validation_service.py                        4 lines  
      └── test_workflow_gateway_tools.py                   90 lines  
