from __future__ import annotations

from importlib import import_module

patches = import_module("offline_mirror.patches")
insert_before_main_bundle_script = patches.insert_before_main_bundle_script
insert_after_main_bundle_script = patches.insert_after_main_bundle_script
strip_topnav_branding = patches.strip_topnav_branding
disable_footer_factory_reset_button = patches.disable_footer_factory_reset_button
disable_welcome_advanced_options_panel = patches.disable_welcome_advanced_options_panel
inject_more_tab_factory_reset_controls = patches.inject_more_tab_factory_reset_controls
inject_more_tab_factory_reset_modal_state = patches.inject_more_tab_factory_reset_modal_state
audit_external_url_hosts = patches.audit_external_url_hosts
validate_offline_connect_src = patches.validate_offline_connect_src
resolve_main_bundle_path = patches.resolve_main_bundle_path
disable_ai_helper_lazy_import = patches.disable_ai_helper_lazy_import
disable_ai_helper_floating_render = patches.disable_ai_helper_floating_render
neutralize_iot_download_getter = patches.neutralize_iot_download_getter
patch_device_not_supported_modal_flow = patches.patch_device_not_supported_modal_flow
patch_company_mapping_allowlist = patches.patch_company_mapping_allowlist
hide_external_footer_links_section = patches.hide_external_footer_links_section
has_visible_external_footer_links = patches.has_visible_external_footer_links
apply_linux_patches = patches.apply_linux_patches
MORE_TAB_FACTORY_RESET_SECTION_LEGACY = patches.MORE_TAB_FACTORY_RESET_SECTION_LEGACY
MORE_TAB_NOTIFICATIONS_ANCHOR = patches.MORE_TAB_NOTIFICATIONS_ANCHOR


def test_insert_before_main_bundle_script_injects_once() -> None:
    html = '<head>\n<script type="module" crossorigin src="./js/index.1c916957.js"></script>\n</head>'
    tag = '<script src="./js/offline-runtime-guard.js"></script>'
    updated, changed = insert_before_main_bundle_script(html, tag)
    assert changed
    assert tag in updated

    updated_again, changed_again = insert_before_main_bundle_script(updated, tag)
    assert not changed_again
    assert updated_again.count(tag) == 1


def test_insert_after_main_bundle_script_injects_once() -> None:
    html = '<head>\n<script type="module" crossorigin src="./js/index.1c916957.js"></script>\n</head>'
    tag = '<script defer src="./js/theme-switcher.js"></script>'
    updated, changed = insert_after_main_bundle_script(html, tag)
    assert changed
    assert tag in updated

    updated_again, changed_again = insert_after_main_bundle_script(updated, tag)
    assert not changed_again
    assert updated_again.count(tag) == 1


def test_strip_topnav_branding_replaces_exact_header_block() -> None:
    header_logo_block = (
        'vt?d.jsx(P,{type:"上下",w:"full",style:{paddingTop:"67px",paddingBottom:"43px"},'
        'children:d.jsx("img",{src:eo()+"/topnav_logo.png",alt:v.driverDisplayName,height:87})}):'
        'd.jsx(P,{type:"上下",w:"full",style:{paddingTop:"67px",paddingBottom:"43px"},'
        'children:d.jsx("img",{src:eo(v.getCurrentDevice().deviceType.company)+"/topnav_logo.png",alt:v.driverDisplayName,height:87})})'
    )
    bundle = f"children:[{header_logo_block},k.map((L,F)=>L.enabled)]"

    updated, changed = strip_topnav_branding(bundle)

    assert changed
    assert "topnav_logo.png" not in updated
    assert updated == "children:[null,k.map((L,F)=>L.enabled)]"


def test_strip_topnav_branding_matches_variable_name_changes() -> None:
    header_logo_block = (
        'isDesktop?d.jsx(P,{type:"上下",w:"full",style:{paddingTop:"67px",paddingBottom:"43px"},'
        'children:d.jsx("img",{src:resolveCompany()+"/topnav_logo.png",alt:state.driverDisplayName,height:87})}):'
        'd.jsx(P,{type:"上下",w:"full",style:{paddingTop:"67px",paddingBottom:"43px"},'
        'children:d.jsx("img",{src:resolveCompany(state.getCurrentDevice().deviceType.company)+"/topnav_logo.png",alt:state.driverDisplayName,height:87})})'
    )

    updated, changed = strip_topnav_branding(header_logo_block)

    assert changed
    assert updated == "null"


def test_disable_footer_factory_reset_button_replaces_exact_prefix() -> None:
    footer_block = (
        '!Lr.isDanglePage&&d.jsx(P,{type:"左右",style:{cursor:"pointer",whiteSpace:"nowrap",color:"black"},'
        'onClick:()=>{if(v.宏编辑.isRecord!=="stop"){Pe.error(e("请先停止录制"),v.toastOptions);return}v.恢复出厂设置()},'
        'children:[d.jsx(B,{src:ee("common/reFactorySet.png"),w:16,h:16}),'
        'd.jsx(T,{type:"三级标题栏",text:e("恢复出厂设置")})]})'
    )

    updated, changed = disable_footer_factory_reset_button(footer_block)

    assert changed
    assert updated.startswith("!1&&d.jsx(P")
    assert 'v.恢复出厂设置()' in updated


def test_disable_footer_factory_reset_button_matches_variable_name_changes() -> None:
    footer_block = (
        '!page.isDanglePage&&d.jsx(P,{type:"左右",style:{cursor:"pointer",whiteSpace:"nowrap",color:"black"},'
        'onClick:()=>{if(store.宏编辑.isRecord!=="stop"){toast.error(i18n("请先停止录制"),store.toastOptions);return}store.恢复出厂设置()},'
        'children:[d.jsx(B,{src:asset("common/reFactorySet.png"),w:16,h:16}),'
        'd.jsx(T,{type:"三级标题栏",text:i18n("恢复出厂设置")})]})'
    )

    updated, changed = disable_footer_factory_reset_button(footer_block)

    assert changed
    assert updated.startswith("!1&&d.jsx(P")
    assert 'store.恢复出厂设置()' in updated


def test_disable_welcome_advanced_options_panel_replaces_exact_prefix() -> None:
    panel = (
        '!C&&e.jsx(s,{type:"上下___交叉轴居左",style:{position:"fixed",bottom:"5%",right:"2%",zIndex:1e3,transition:"all 0.3s ease"},children:p?'
        'e.jsxs(s,{children:["advanced"]}):e.jsxs(s,{children:["collapsed"]})})'
    )

    updated, changed = disable_welcome_advanced_options_panel(panel)

    assert changed
    assert updated.startswith("!1&&e.jsx(s")
    assert 'children:p?' in updated


def test_disable_welcome_advanced_options_panel_matches_variable_name_changes() -> None:
    panel = (
        '!isElectron&&e.jsx(Container,{type:"上下___交叉轴居左",style:{position:"fixed",bottom:"5%",right:"2%",zIndex:1e3,transition:"all 0.3s ease"},'
        'children:isExpanded?renderOpen():renderClosed()})'
    )

    updated, changed = disable_welcome_advanced_options_panel(panel)

    assert changed
    assert updated.startswith("!1&&e.jsx(Container")
    assert "children:isExpanded?" in updated


def test_disable_welcome_advanced_options_panel_is_idempotent() -> None:
    panel = (
        '!1&&e.jsx(s,{type:"上下___交叉轴居左",style:{position:"fixed",bottom:"5%",right:"2%",zIndex:1e3,transition:"all 0.3s ease"},children:p?'
        'e.jsxs(s,{children:["advanced"]}):e.jsxs(s,{children:["collapsed"]})})'
    )

    updated, changed = disable_welcome_advanced_options_panel(panel)

    assert not changed
    assert updated == panel


def test_inject_more_tab_factory_reset_controls_inserts_section_once() -> None:
    anchor = (
        'u.isUseIotSDK&&e.jsxs(r,{type:"上下___交叉轴居左",w:"full",style:{gap:"16px"},'
        'children:[e.jsx(r,{type:"左右",style:{gap:"10px"},children:e.jsx(c,{type:"一级标题栏_高亮",text:t.通知设置||"通知设置"'
    )
    content = f"prefix,{anchor},suffix"

    updated, changed = inject_more_tab_factory_reset_controls(content)

    assert changed
    assert "setFactoryResetConfirmVisible(!0)" in updated
    assert "factoryResetConfirmVisible&&e.jsxs(e.Fragment" in updated
    assert "Warning: factory reset will erase all custom settings" in updated
    assert "window.alert" not in updated
    assert "window.confirm" not in updated

    updated_again, changed_again = inject_more_tab_factory_reset_controls(updated)
    assert not changed_again


def test_inject_more_tab_factory_reset_modal_state_inserts_once() -> None:
    content = (
        'prefix,const f=s.toastOptions;!O&&u.isUseIotSDK,i.useState(!1),i.useState(0);'
        'const[L,V]=i.useState(!1),suffix'
    )

    updated, changed = inject_more_tab_factory_reset_modal_state(content)

    assert changed
    assert "const[factoryResetConfirmVisible,setFactoryResetConfirmVisible]=i.useState(!1);" in updated

    updated_again, changed_again = inject_more_tab_factory_reset_modal_state(updated)
    assert not changed_again


def test_inject_more_tab_factory_reset_controls_replaces_legacy_block() -> None:
    content = f"prefix,{MORE_TAB_FACTORY_RESET_SECTION_LEGACY}{MORE_TAB_NOTIFICATIONS_ANCHOR},suffix"

    updated, changed = inject_more_tab_factory_reset_controls(content)

    assert changed
    assert "window.alert" not in updated
    assert "window.confirm" not in updated
    assert "setFactoryResetConfirmVisible(!0)" in updated


def test_audit_external_url_hosts_flags_blocked_vendor_hosts(tmp_path) -> None:
    chunk = tmp_path / "js" / "index.fake.js"
    chunk.parent.mkdir(parents=True)
    chunk.write_text('const api="https://api2.qmk.top:3816/api/v2";', encoding="utf-8")

    blocked_hits, unknown_hosts = audit_external_url_hosts(tmp_path)

    assert blocked_hits
    assert any("api2.qmk.top" in hit for hit in blocked_hits)
    assert not unknown_hosts


def test_audit_external_url_hosts_allows_reference_and_local_hosts(tmp_path) -> None:
    chunk = tmp_path / "js" / "index.fake.js"
    chunk.parent.mkdir(parents=True)
    chunk.write_text(
        'const xmlns="http://www.w3.org/2000/svg";'
        'const docs="https://github.com/example/repo";'
        'const local="http://127.0.0.1:6015/version";',
        encoding="utf-8",
    )

    blocked_hits, unknown_hosts = audit_external_url_hosts(tmp_path)

    assert not blocked_hits
    assert not unknown_hosts


def test_audit_external_url_hosts_collects_unknown_hosts(tmp_path) -> None:
    chunk = tmp_path / "js" / "index.fake.js"
    chunk.parent.mkdir(parents=True)
    chunk.write_text('const docs="https://example.com/help";', encoding="utf-8")

    blocked_hits, unknown_hosts = audit_external_url_hosts(tmp_path)

    assert not blocked_hits
    assert unknown_hosts["example.com"] == 1


def test_validate_offline_connect_src_accepts_local_only_policy(tmp_path) -> None:
    index_html = tmp_path / "index.html"
    index_html.write_text(
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src \'self\'; connect-src \'self\' http://127.0.0.1:* '
        'http://localhost:* ws://127.0.0.1:* ws://localhost:*;" />',
        encoding="utf-8",
    )

    violations = validate_offline_connect_src(index_html)

    assert not violations


def test_validate_offline_connect_src_rejects_remote_tokens(tmp_path) -> None:
    index_html = tmp_path / "index.html"
    index_html.write_text(
        '<meta http-equiv="Content-Security-Policy" '
        'content="default-src \'self\'; connect-src \'self\' https://api.example.com;" />',
        encoding="utf-8",
    )

    violations = validate_offline_connect_src(index_html)

    assert violations
    assert any("https://api.example.com" in violation for violation in violations)


def test_resolve_main_bundle_path_prefers_html_referenced_bundle(tmp_path) -> None:
    js_dir = tmp_path / "js"
    js_dir.mkdir(parents=True)
    stale = js_dir / "index.older.js"
    active = js_dir / "index.active.js"
    stale.write_text("stale", encoding="utf-8")
    active.write_text("active", encoding="utf-8")

    (tmp_path / "index.html").write_text(
        '<script type="module" crossorigin src="./js/index.active.js"></script>',
        encoding="utf-8",
    )

    assert resolve_main_bundle_path(tmp_path) == active


def test_disable_ai_helper_lazy_import_regex_tracks_current_assets() -> None:
    content = (
        'Goe=y.lazy(()=>p(()=>import("./c810c58d.js"),["./c810c58d.js","..\\assets\\css\\AiFloat.db6806a6.css"],'
        'import.meta.url).then(e=>({default:e.AiFloat})))'
    )

    updated, changed, removed_paths = disable_ai_helper_lazy_import(content)

    assert changed
    assert "Goe=()=>null" in updated
    assert "AiFloat" not in updated
    assert "js/c810c58d.js" in removed_paths
    assert "assets/css/AiFloat.db6806a6.css" in removed_paths


def test_disable_ai_helper_floating_render_regex_handles_variable_drift() -> None:
    content = (
        '!ux.isNoAIAssistant()&&d.jsx(y.Suspense,{fallback:d.jsx(d.Fragment,{}),'
        'children:d.jsx(Goe,{deviceName:v.getCurrentDevice().deviceType.displayName??"",'
        'useProductionServer:!0,company:v.getCurrentDevice().deviceType.company,'
        'deviceType:v.getCurrentDevice().deviceType.type})})'
    )

    updated, changed = disable_ai_helper_floating_render(content)

    assert changed
    assert updated == "!1"


def test_neutralize_iot_download_getter_regex_handles_variable_drift() -> None:
    content = (
        'get iotDownloadUrl(){const e=this.getPlatform();return e?`https://news.rongyuan.tech/iot_driver/${e}/iot_manager_setup_v${e==="mac"?X_:$d}.${e==="mac"?"dmg":"exe"}?${new Date().getTime()}`:void 0}'
        'get vcredistx86DownloadUrl(){return"https://aka.ms/vs/17/release/vc_redist.x86.exe"}'
    )

    updated, changed = neutralize_iot_download_getter(content)

    assert changed
    assert "news.rongyuan.tech/iot_driver" not in updated
    assert 'get iotDownloadUrl(){return"#"}get vcredistx86DownloadUrl()' in updated


def test_patch_device_not_supported_modal_flow_handles_variable_drift() -> None:
    content = (
        's.errorCode===Xs.DEVICE_NOT_SUPPORTED?'
        '(v.isDeviceSupportedInNewDriver=!1,v.showJumpToOldDriverModal=!0):'
        '(v.isDeviceSupportedInNewDriver=!0,v.showJumpToOldDriverModal=!1)'
    )

    updated, changed = patch_device_not_supported_modal_flow(content)

    assert changed
    assert "isUseIotSDK" in updated
    assert "DEVICE_NOT_SUPPORTED?(v.isUseIotSDK?" in updated


def test_patch_company_mapping_allowlist_handles_set_name_drift() -> None:
    content = "let a=U7.find(u=>u.id===e&&!n.has(u.company)&&!RT.has(u.displayName));"

    updated, changed = patch_company_mapping_allowlist(content)

    assert changed
    assert '(!n.has(u.company)||u.company==="EWEADNV")&&!RT.has(u.displayName)' in updated


def test_hide_external_footer_links_section_handles_host_gated_render() -> None:
    content = (
        'children:!gt&&(window.location.hostname.includes("qmk.top")||'
        'window.location.hostname.includes("gearhub.top")||'
        'window.location.hostname==="localhost"||'
        'window.location.hostname.includes("127.0.0.1"))&&d.jsxs(P,{children:["footer"]})'
    )

    updated, changed = hide_external_footer_links_section(content)

    assert changed
    assert updated.startswith('children:!1&&d.jsxs(P,{')
    assert not has_visible_external_footer_links(updated)


def test_apply_linux_patches_scans_reachable_files_only(tmp_path) -> None:
    js_dir = tmp_path / "js"
    css_dir = tmp_path / "assets" / "css"
    js_dir.mkdir(parents=True)
    css_dir.mkdir(parents=True)

    active_index = js_dir / "index.active.js"
    stale_index = js_dir / "index.stale.js"
    ai_chunk = js_dir / "c810c58d.js"
    ai_css = css_dir / "AiFloat.db6806a6.css"

    stale_index.write_text("AiFloat https://api2.qmk.top:3816/api/v2", encoding="utf-8")
    ai_chunk.write_text("export const AiFloat = true;", encoding="utf-8")
    ai_css.write_text(".ai { color: red; }", encoding="utf-8")

    active_index.write_text(
        'Goe=y.lazy(()=>p(()=>import("./c810c58d.js"),["./c810c58d.js","..\\assets\\css\\AiFloat.db6806a6.css"],import.meta.url).then(e=>({default:e.AiFloat})));'
        '!ux.isNoAIAssistant()&&d.jsx(y.Suspense,{fallback:d.jsx(d.Fragment,{}),children:d.jsx(Goe,{deviceName:v.getCurrentDevice().deviceType.displayName??"",useProductionServer:!0,company:v.getCurrentDevice().deviceType.company,deviceType:v.getCurrentDevice().deviceType.type})});'
        'window.open("https://beian.miit.gov.cn/#/Integrated/index","_blank");'
        'window.open("https://qmk.top/gear-lab","_self");'
        'let a=U7.find(u=>u.id===e&&!n.has(u.company)&&!RT.has(u.displayName));'
        'oldDriverUrl=window.location.hostname.toLowerCase().includes("qmk")?"https://iotdriver.qmk.top/":(window.location.hostname.toLowerCase().includes("gearhub"),"https://iotdriver.gearhub.top/");'
        'get iotDownloadUrl(){const e=this.getPlatform();return e?`https://news.rongyuan.tech/iot_driver/${e}/iot_manager_setup_v${e==="mac"?X_:$d}.${e==="mac"?"dmg":"exe"}?${new Date().getTime()}`:void 0}get vcredistx86DownloadUrl(){return"https://aka.ms/vs/17/release/vc_redist.x86.exe"}get vcredistx64DownloadUrl(){return"https://aka.ms/vs/17/release/vc_redist.x64.exe"};'
        'ff="https://api3.rongyuan.tech:3816/api/v2",gf="https://api3.rongyuan.tech:3816/download/bit_image_file"):(ff="https://api2.qmk.top:3816/api/v2",gf="https://api2.qmk.top:3816/download/bit_image_file");'
        'const _x=ff,GF=gf,YF="https://api2.rongyuan.tech:3816/api/v2",by="https://api2.rongyuan.tech:3816/download",$F=px&&!1||gt||sd?"https://api.rongyuan.tech:3814/v1":"https://api2.qmk.top:3814/v1",',
        encoding="utf-8",
    )

    (tmp_path / "index.html").write_text(
        '<!doctype html><html><head><meta name="viewport" content="width=device-width" />'
        '<script type="module" crossorigin src="./js/index.active.js"></script></head><body></body></html>',
        encoding="utf-8",
    )

    notes = apply_linux_patches(tmp_path)

    updated_active = active_index.read_text(encoding="utf-8")
    assert "AiFloat" not in updated_active
    assert "beian.miit.gov.cn" not in updated_active
    assert "qmk.top/gear-lab" not in updated_active
    assert "api2.qmk.top:3816" not in updated_active
    assert "api.rongyuan.tech:3814" not in updated_active
    assert "DEVICE_NOT_SUPPORTED?(v.isDeviceSupportedInNewDriver=!1,v.showJumpToOldDriverModal=!0)" not in updated_active
    assert "window.location.hostname.includes(\"qmk.top\")||window.location.hostname.includes(\"gearhub.top\")" not in updated_active
    assert "!n.has(u.company)&&!RT.has(u.displayName)" not in updated_active
    assert '(!n.has(u.company)||u.company==="EWEADNV")&&!RT.has(u.displayName)' in updated_active
    assert "/offline-disabled/api/v2" in updated_active
    assert not ai_chunk.exists()
    assert not ai_css.exists()
    assert any("Patching active runtime bundle: index.active.js." == note for note in notes)
