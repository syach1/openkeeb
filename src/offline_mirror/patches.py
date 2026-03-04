from __future__ import annotations

import re
from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urljoin, urlsplit

from offline_mirror.crawl import (
    clean_url,
    extract_css_refs,
    extract_html_refs,
    extract_js_refs,
    to_local_path,
)

from offline_mirror.constants import (
    BALANCED_ALLOWED_EXTERNAL_REFERENCE_HOSTS,
    BALANCED_BLOCKED_EXTERNAL_HOST_SUFFIXES,
    EXTERNAL_URL_RE,
    OFFLINE_CSP_CONTENT,
    OFFLINE_CONNECT_SRC_ALLOWED_TOKENS,
    PERMANENT_BLOCKED_MARKERS,
    PERMANENT_BLOCKED_SCAN_SUFFIXES,
    THEME_COLOR_REPLACEMENTS,
)
from offline_mirror.theme_assets import ensure_theme_assets


@dataclass(frozen=True)
class ReplaceRule:
    old: str
    new: str
    note: str


CORE_PATCH_RULES: tuple[ReplaceRule, ...] = (
    ReplaceRule(
        old='Fi.platform==="other"&&(i=!1)',
        new='(Fi.platform==="other"||Fi.platform==="linux")&&(i=!1)',
        note="Patched setIOTSwitch to disable IOT mode on Linux.",
    ),
    ReplaceRule(
        old='Fi.platform==="other"?t=!1:',
        new='(Fi.platform==="other"||Fi.platform==="linux")?t=!1:',
        note="Patched getIOTSwitch to keep Linux in WebHID mode.",
    ),
    ReplaceRule(
        old='o.errorCode===$s.DEVICE_NOT_SUPPORTED?(v.isDeviceSupportedInNewDriver=!1,v.showJumpToOldDriverModal=!0):(v.isDeviceSupportedInNewDriver=!0,v.showJumpToOldDriverModal=!1)',
        new='o.errorCode===$s.DEVICE_NOT_SUPPORTED?(v.isUseIotSDK?(v.isDeviceSupportedInNewDriver=!1,v.showJumpToOldDriverModal=!0):(v.isDeviceSupportedInNewDriver=!0,v.showJumpToOldDriverModal=!1)):(v.isDeviceSupportedInNewDriver=!0,v.showJumpToOldDriverModal=!1)',
        note="Patched DEVICE_NOT_SUPPORTED flow to suppress old-driver modal in WebHID mode.",
    ),
    ReplaceRule(
        old='!n.has(u.company)&&!AT.has(u.displayName)',
        new='(!n.has(u.company)||u.company==="EWEADNV")&&!AT.has(u.displayName)',
        note="Patched device ID mapping to allow EWEADNV devices in web offline mode.",
    ),
    ReplaceRule(
        old='else return"company/company_"+e',
        new='else return"company/company_"+(e??Ya.currentCompany)',
        note="Patched company path helper to avoid undefined company asset path.",
    ),
    ReplaceRule(
        old='async setWebClientIotVersionFromIotConnector(){if(this.webClientIotVersionFromIotConnector!=="")return;const e=await Kt.getVersion();e!==void 0&&(this.webClientIotVersionFromIotConnector=e.baseVersion)}',
        new='async setWebClientIotVersionFromIotConnector(){if(this.webClientIotVersionFromIotConnector!==""||!this.isUseIotSDK)return;const e=await Kt.getVersion();e!==void 0&&(this.webClientIotVersionFromIotConnector=e.baseVersion)}',
        note="Patched web IOT version preload to skip GetVersion when IOT mode is disabled.",
    ),
    ReplaceRule(
        old='async getClientWebIotManagerVersion(){return(await Kt.getVersion())?.baseVersion}',
        new='async getClientWebIotManagerVersion(){if(!this.isUseIotSDK)return;return(await Kt.getVersion())?.baseVersion}',
        note="Patched client IOT manager version check to avoid localhost:6015 requests in WebHID mode.",
    ),
)


TOPNAV_BRANDING_EXACT = (
    'vt?d.jsx(P,{type:"上下",w:"full",style:{paddingTop:"67px",paddingBottom:"43px"},'
    'children:d.jsx("img",{src:eo()+"/topnav_logo.png",alt:v.driverDisplayName,height:87})}):'
    'd.jsx(P,{type:"上下",w:"full",style:{paddingTop:"67px",paddingBottom:"43px"},'
    'children:d.jsx("img",{src:eo(v.getCurrentDevice().deviceType.company)+"/topnav_logo.png",alt:v.driverDisplayName,height:87})})'
)

TOPNAV_BRANDING_PATTERN = re.compile(
    r'[A-Za-z_$][\w$]*\?d\.jsx\(P,\{type:"上下",w:"full",style:\{paddingTop:"67px",paddingBottom:"43px"\},'
    r'children:d\.jsx\("img",\{src:[^}]+/topnav_logo\.png",alt:[^}]+height:87\}\)\}\):'
    r'd\.jsx\(P,\{type:"上下",w:"full",style:\{paddingTop:"67px",paddingBottom:"43px"\},'
    r'children:d\.jsx\("img",\{src:[^}]+/topnav_logo\.png",alt:[^}]+height:87\}\)\}\)'
)


def strip_topnav_branding(content: str) -> tuple[str, bool]:
    updated = content.replace(TOPNAV_BRANDING_EXACT, "null")
    if updated != content:
        return updated, True

    updated, replacements = TOPNAV_BRANDING_PATTERN.subn("null", content, count=1)
    return updated, replacements > 0


FOOTER_FACTORY_RESET_PREFIX = (
    '!Lr.isDanglePage&&d.jsx(P,{type:"左右",style:{cursor:"pointer",whiteSpace:"nowrap",color:"black"},'
    'onClick:()=>{if(v.宏编辑.isRecord!=="stop"){Pe.error(e("请先停止录制"),v.toastOptions);return}v.恢复出厂设置()},'
)

FOOTER_FACTORY_RESET_DISABLED_PREFIX = (
    '!1&&d.jsx(P,{type:"左右",style:{cursor:"pointer",whiteSpace:"nowrap",color:"black"},'
    'onClick:()=>{if(v.宏编辑.isRecord!=="stop"){Pe.error(e("请先停止录制"),v.toastOptions);return}v.恢复出厂设置()},'
)

FOOTER_FACTORY_RESET_PATTERN = re.compile(
    r'![A-Za-z_$][\w$]*\.isDanglePage&&d\.jsx\(P,\{type:"左右",style:\{cursor:"pointer",whiteSpace:"nowrap",color:"black"\},'
    r'onClick:\(\)=>\{if\([A-Za-z_$][\w$]*\.宏编辑\.isRecord!=="stop"\)\{[A-Za-z_$][\w$]*\.error\([A-Za-z_$][\w$]*\("请先停止录制"\),[A-Za-z_$][\w$]*\.toastOptions\);return\}[A-Za-z_$][\w$]*\.恢复出厂设置\(\)\},'
)


def disable_footer_factory_reset_button(content: str) -> tuple[str, bool]:
    if FOOTER_FACTORY_RESET_DISABLED_PREFIX in content:
        return content, False

    updated = content.replace(FOOTER_FACTORY_RESET_PREFIX, FOOTER_FACTORY_RESET_DISABLED_PREFIX, 1)
    if updated != content:
        return updated, True

    def _disable_prefix(match: re.Match[str]) -> str:
        full = match.group(0)
        return "!1&&" + full.split("&&", 1)[1]

    updated, replacements = FOOTER_FACTORY_RESET_PATTERN.subn(_disable_prefix, content, count=1)
    return updated, replacements > 0


WELCOME_ADVANCED_OPTIONS_PREFIX = (
    '!C&&e.jsx(s,{type:"上下___交叉轴居左",style:{position:"fixed",bottom:"5%",right:"2%",zIndex:1e3,transition:"all 0.3s ease"},children:p?'
)

WELCOME_ADVANCED_OPTIONS_DISABLED_PREFIX = (
    '!1&&e.jsx(s,{type:"上下___交叉轴居左",style:{position:"fixed",bottom:"5%",right:"2%",zIndex:1e3,transition:"all 0.3s ease"},children:p?'
)

WELCOME_ADVANCED_OPTIONS_PATTERN = re.compile(
    r'![A-Za-z_$][\w$]*&&e\.jsx\([A-Za-z_$][\w$]*,\{type:"上下___交叉轴居左",style:\{position:"fixed",bottom:"5%",right:"2%",zIndex:1e3,transition:"all 0\.3s ease"\},children:[A-Za-z_$][\w$]*\?'
)

WELCOME_ADVANCED_OPTIONS_DISABLED_PATTERN = re.compile(
    r'!1&&e\.jsx\([A-Za-z_$][\w$]*,\{type:"上下___交叉轴居左",style:\{position:"fixed",bottom:"5%",right:"2%",zIndex:1e3,transition:"all 0\.3s ease"\},children:[A-Za-z_$][\w$]*\?'
)


def disable_welcome_advanced_options_panel(content: str) -> tuple[str, bool]:
    if WELCOME_ADVANCED_OPTIONS_DISABLED_PATTERN.search(content):
        return content, False

    updated = content.replace(WELCOME_ADVANCED_OPTIONS_PREFIX, WELCOME_ADVANCED_OPTIONS_DISABLED_PREFIX, 1)
    if updated != content:
        return updated, True

    def _disable_prefix(match: re.Match[str]) -> str:
        full = match.group(0)
        return "!1&&" + full.split("&&", 1)[1]

    updated, replacements = WELCOME_ADVANCED_OPTIONS_PATTERN.subn(_disable_prefix, content, count=1)
    return updated, replacements > 0


MORE_TAB_FACTORY_RESET_CARD_WARNING = (
    "Warning: factory reset will erase all custom settings (macros, Fn layers, and lighting) "
    "and restore device defaults."
)

MORE_TAB_FACTORY_RESET_MODAL_WARNING = (
    "This will erase all custom settings (macros, Fn layers, and lighting). "
    "This action cannot be undone."
)

MORE_TAB_NOTIFICATIONS_ANCHOR = (
    'u.isUseIotSDK&&e.jsxs(r,{type:"上下___交叉轴居左",w:"full",style:{gap:"16px"},'
    'children:[e.jsx(r,{type:"左右",style:{gap:"10px"},children:e.jsx(c,{type:"一级标题栏_高亮",text:t.通知设置||"通知设置"'
)

MORE_TAB_FACTORY_RESET_STATE_ANCHOR = (
    'const f=s.toastOptions;!O&&u.isUseIotSDK,i.useState(!1),i.useState(0);'
)

MORE_TAB_FACTORY_RESET_STATE_REPLACEMENT = (
    'const f=s.toastOptions;const[factoryResetConfirmVisible,setFactoryResetConfirmVisible]=i.useState(!1);'
    '!O&&u.isUseIotSDK,i.useState(!1),i.useState(0);'
)

MORE_TAB_FACTORY_RESET_STATE_PATTERN = re.compile(
    r'const [A-Za-z_$][\w$]*=[A-Za-z_$][\w$]*\.toastOptions;'
    r'![A-Za-z_$][\w$]*&&[A-Za-z_$][\w$]*\.isUseIotSDK,'
    r'(?P<react>[A-Za-z_$][\w$]*)\.useState\(!1\),(?P=react)\.useState\(0\);'
)

MORE_TAB_FACTORY_RESET_SECTION = (
    'e.jsx(r,{type:"上下___交叉轴居左",w:"full",style:{gap:"16px"},children:e.jsxs(r,{type:"上下",w:"full",'
    'style:{padding:"24px",background:"white",boxShadow:"0px 0px 4px rgba(0, 0, 0, 0.10)",borderRadius:"12px",gap:"16px"},'
    'children:[e.jsx(c,{type:"一级标题栏_高亮",text:t.恢复出厂设置||"Restore Factory Settings",style:{color:"#3E3E3E",fontSize:"24px",fontFamily:"Source Han Sans SC",fontWeight:"500"}}),'
    'e.jsx(c,{type:"提示文本",text:"Warning: factory reset will erase all custom settings (macros, Fn layers, and lighting) and restore device defaults.",wrap:!0,style:{color:"#B2412E",fontSize:"16px",fontFamily:"Source Han Sans SC",fontWeight:"500",lineHeight:"1.5"}}),'
    'e.jsx(A,{text:t.恢复出厂设置||"Restore Factory Settings",onClick:()=>{if(s.宏编辑.isRecord!=="stop"){w.error(t.请先停止录制||"Please stop recording first",f);return}setFactoryResetConfirmVisible(!0)},style:{alignSelf:"flex-start"}}),'
    'factoryResetConfirmVisible&&e.jsxs(e.Fragment,{children:[e.jsx(r,{type:"左右___主轴居中",w:"full",h:"full",style:{backgroundColor:"rgba(0, 0, 0, 0.55)",position:"fixed",top:0,left:0,zIndex:1999}}),'
    'e.jsxs(r,{type:"上下",w:520,style:{maxWidth:"90vw",background:"white",padding:"24px",boxShadow:"0px 16px 48px rgba(0, 0, 0, 0.25)",borderRadius:"12px",gap:"16px",position:"fixed",top:"50%",left:"50%",transform:"translate(-50%, -50%)",zIndex:2e3},'
    'children:[e.jsx(c,{type:"一级标题栏_高亮",text:t.恢复出厂设置||"Restore Factory Settings",style:{color:"#2D2D2D",fontSize:"24px",fontFamily:"Source Han Sans SC",fontWeight:"500"}}),'
    'e.jsx(c,{type:"提示文本",text:"This will erase all custom settings (macros, Fn layers, and lighting). This action cannot be undone.",wrap:!0,style:{color:"#B2412E",fontSize:"18px",fontFamily:"Source Han Sans SC",fontWeight:"500",lineHeight:"1.5"}}),'
    'e.jsxs(r,{type:"左右",w:"full",style:{justifyContent:"flex-end",gap:"12px"},children:[e.jsx(A,{text:t.取消||"Cancel",onClick:()=>setFactoryResetConfirmVisible(!1),style:{padding:"8px 28px"}}),'
    'e.jsx(A,{text:t.确认||"Confirm",onClick:()=>{setFactoryResetConfirmVisible(!1),s.恢复出厂设置()},style:{padding:"8px 28px"}})]})]})]}),'
    ']})}),'
)


MORE_TAB_FACTORY_RESET_SECTION_LEGACY = (
    'e.jsx(r,{type:"上下___交叉轴居左",w:"full",style:{gap:"16px"},children:e.jsxs(r,{type:"上下",w:"full",'
    'style:{padding:"24px",background:"white",boxShadow:"0px 0px 4px rgba(0, 0, 0, 0.10)",borderRadius:"12px",gap:"16px"},'
    'children:[e.jsx(c,{type:"一级标题栏_高亮",text:t.恢复出厂设置||"Restore Factory Settings",style:{color:"#3E3E3E",fontSize:"24px",fontFamily:"Source Han Sans SC",fontWeight:"500"}}),'
    'e.jsx(c,{type:"提示文本",text:"Warning: this button will factory reset your device. All your setting like macro / fn layer / light will be reset to factory default.",wrap:!0,style:{color:"#666666",fontSize:"16px",fontFamily:"Source Han Sans SC",fontWeight:"400",lineHeight:"1.5"}}),'
    'e.jsx(A,{text:t.恢复出厂设置||"Restore Factory Settings",onClick:()=>{if(s.宏编辑.isRecord!=="stop"){window.alert(t.请先停止录制||"Please stop recording first");return}const p="Warning: this button will factory reset your device. All your setting like macro / fn layer / light will be reset to factory default.";window.confirm(p)&&s.恢复出厂设置()},style:{alignSelf:"flex-start"}})]})}),'
)


def inject_more_tab_factory_reset_modal_state(content: str) -> tuple[str, bool]:
    if "factoryResetConfirmVisible" in content and "setFactoryResetConfirmVisible" in content:
        return content, False

    updated = content.replace(MORE_TAB_FACTORY_RESET_STATE_ANCHOR, MORE_TAB_FACTORY_RESET_STATE_REPLACEMENT, 1)
    if updated != content:
        return updated, True

    def _inject_state(match: re.Match[str]) -> str:
        full = match.group(0)
        react_var = match.group("react")
        insertion = f"const[factoryResetConfirmVisible,setFactoryResetConfirmVisible]={react_var}.useState(!1);"
        return full.replace(";", ";" + insertion, 1)

    updated, replacements = MORE_TAB_FACTORY_RESET_STATE_PATTERN.subn(_inject_state, content, count=1)
    return updated, replacements > 0


def inject_more_tab_factory_reset_controls(content: str) -> tuple[str, bool]:
    updated = content
    changed = False

    updated_without_legacy = updated.replace(MORE_TAB_FACTORY_RESET_SECTION_LEGACY, "", 1)
    if updated_without_legacy != updated:
        updated = updated_without_legacy
        changed = True

    if (
        MORE_TAB_FACTORY_RESET_CARD_WARNING in updated
        and MORE_TAB_FACTORY_RESET_MODAL_WARNING in updated
        and "setFactoryResetConfirmVisible(!0)" in updated
    ):
        return updated, changed

    if MORE_TAB_NOTIFICATIONS_ANCHOR not in updated:
        return updated, changed

    updated = updated.replace(
        MORE_TAB_NOTIFICATIONS_ANCHOR,
        MORE_TAB_FACTORY_RESET_SECTION + MORE_TAB_NOTIFICATIONS_ANCHOR,
        1,
    )
    return updated, updated != content


def patch_more_tab_controls(site_root: Path) -> list[str]:
    """Disable firmware-upgrade and IOT-enable actions in More tab."""
    notes: list[str] = []
    js_dir = site_root / "js"
    if not js_dir.exists():
        return notes

    firmware_button_exact = (
        'e.jsx(A,{text:t.固件升级||"固件升级",onClick:M,loading:m,loadingText:t.获取中||"获取中"})',
        'e.jsx(A,{text:t.固件升级||"固件升级",onClick:void 0,loading:m,loadingText:t.获取中||"获取中",disabled:!0})',
    )
    firmware_button_desktop_exact = (
        'e.jsx(I,{w:180,text:F?t.获取中:t.固件升级,onClick:Z,disabled:F})',
        'e.jsx(I,{w:180,text:F?t.获取中:t.固件升级,onClick:void 0,disabled:!0})',
    )
    iot_enable_toggle_exact = (
        'e.jsx(ae,{isIotEnabled:u.isUseIotSDK,onClick:u.isUseIotSDK?K:z,enableText:t.启用iot驱动||"启用IOT驱动",disableText:t.关闭iot驱动||"关闭IOT驱动"})',
        'e.jsx(ae,{isIotEnabled:u.isUseIotSDK,onClick:u.isUseIotSDK?K:void 0,disabled:!u.isUseIotSDK,enableText:t.启用iot驱动||"启用IOT驱动",disableText:t.关闭iot驱动||"关闭IOT驱动"})',
    )

    firmware_button_pattern = re.compile(
        r'e\.jsx\(A,\{text:t\.固件升级\|\|"固件升级",onClick:[^,}]+,loading:(?P<loading>[^,}]+),loadingText:t\.获取中\|\|"获取中"\}\)'
    )
    firmware_button_desktop_pattern = re.compile(
        r'e\.jsx\(I,\{w:180,text:(?P<text_expr>[^,}]*t\.固件升级[^,}]*),onClick:[^,}]+,disabled:[^,}]+\}\)'
    )
    iot_enable_toggle_pattern = re.compile(
        r'e\.jsx\(ae,\{isIotEnabled:u\.isUseIotSDK,onClick:u\.isUseIotSDK\?(?P<disable_action>[^:}]+):(?P<enable_action>[^,}]+),enableText:t\.启用iot驱动\|\|"启用IOT驱动",disableText:t\.关闭iot驱动\|\|"关闭IOT驱动"\}\)'
    )

    firmware_patched = False
    iot_enable_patched = False
    welcome_advanced_options_disabled = False
    factory_reset_state_injected = False
    factory_reset_section_injected = False

    for chunk_path in sorted(js_dir.glob("*.js")):
        content = chunk_path.read_text(encoding="utf-8", errors="ignore")
        patched = content

        patched = patched.replace(firmware_button_exact[0], firmware_button_exact[1])
        patched = patched.replace(firmware_button_desktop_exact[0], firmware_button_desktop_exact[1])
        patched = patched.replace(iot_enable_toggle_exact[0], iot_enable_toggle_exact[1])

        patched, fw_regex_count = firmware_button_pattern.subn(
            lambda m: (
                'e.jsx(A,{text:t.固件升级||"固件升级",onClick:void 0,loading:'
                + m.group("loading")
                + ',loadingText:t.获取中||"获取中",disabled:!0})'
            ),
            patched,
        )
        patched, fw_desktop_regex_count = firmware_button_desktop_pattern.subn(
            lambda m: (
                'e.jsx(I,{w:180,text:'
                + m.group("text_expr")
                + ',onClick:void 0,disabled:!0})'
            ),
            patched,
        )
        patched, iot_toggle_regex_count = iot_enable_toggle_pattern.subn(
            lambda m: (
                'e.jsx(ae,{isIotEnabled:u.isUseIotSDK,onClick:u.isUseIotSDK?'
                + m.group("disable_action")
                + ':void 0,disabled:!u.isUseIotSDK,enableText:t.启用iot驱动||"启用IOT驱动",disableText:t.关闭iot驱动||"关闭IOT驱动"})'
            ),
            patched,
        )
        patched, disabled_welcome_advanced_options = disable_welcome_advanced_options_panel(patched)
        patched, injected_factory_reset_state = inject_more_tab_factory_reset_modal_state(patched)
        patched, injected_factory_reset = inject_more_tab_factory_reset_controls(patched)

        if patched != content:
            chunk_path.write_text(patched, encoding="utf-8")

        if (
            firmware_button_exact[0] in content
            or firmware_button_desktop_exact[0] in content
            or fw_regex_count > 0
            or fw_desktop_regex_count > 0
        ):
            firmware_patched = True
        if iot_enable_toggle_exact[0] in content or iot_toggle_regex_count > 0:
            iot_enable_patched = True
        if disabled_welcome_advanced_options:
            welcome_advanced_options_disabled = True
        if injected_factory_reset_state:
            factory_reset_state_injected = True
        if injected_factory_reset:
            factory_reset_section_injected = True

    if firmware_patched:
        notes.append("Disabled More-tab firmware-upgrade action button in runtime chunks.")
    if iot_enable_patched:
        notes.append("Disabled More-tab Enable-IOT-driver action when IOT is currently off.")
    if welcome_advanced_options_disabled:
        notes.append("Disabled first-page Advanced Options panel with IOT-driver toggle action.")
    if factory_reset_state_injected or factory_reset_section_injected:
        notes.append("Moved factory-reset action into More tab with warning text, toast validation, and in-app confirmation modal.")

    return notes


def replace_text(content: str, old: str, new: str, *, count: int = -1) -> tuple[str, bool]:
    if count < 0:
        updated = content.replace(old, new)
    else:
        updated = content.replace(old, new, count)
    return updated, updated != content


def apply_rules(content: str, rules: Iterable[ReplaceRule]) -> tuple[str, list[str]]:
    notes: list[str] = []
    updated = content
    for rule in rules:
        updated, changed = replace_text(updated, rule.old, rule.new)
        if changed:
            notes.append(rule.note)
    return updated, notes


MAIN_BUNDLE_SRC_PATTERN = re.compile(
    r'<script[^>]*src=["\']\./js/(?P<bundle>index\.[^"\']+\.js)["\'][^>]*></script>',
    re.IGNORECASE,
)

AI_HELPER_LAZY_IMPORT_EXACT = (
    'Hoe=y.lazy(()=>p(()=>import("./0afe9811.js"),["./0afe9811.js","..\\assets\\css\\AiFloat.db6806a6.css"],'
    'import.meta.url).then(e=>({default:e.AiFloat})))'
)

AI_HELPER_LAZY_IMPORT_PATTERN = re.compile(
    r'(?P<var>[A-Za-z_$][\w$]*)=y\.lazy\(\(\)=>p\(\(\)=>import\("\./(?P<chunk>[^"\\]+\.js)"\),'
    r'\[(?P<deps>[^\]]*AiFloat[^\]]*)\],import\.meta\.url\)\.then\(e=>\(\{default:e\.AiFloat\}\)\)\)'
)

AI_HELPER_FLOATING_RENDER_PATTERN = re.compile(
    r'![A-Za-z_$][\w$]*\.isNoAIAssistant\(\)&&d\.jsx\(y\.Suspense,\{fallback:d\.jsx\(d\.Fragment,\{\}\),'
    r'children:d\.jsx\([A-Za-z_$][\w$]*,\{deviceName:[^}]+useProductionServer:!0,company:[^}]+deviceType:[^}]+\}\)\}\)'
)

IOT_DOWNLOAD_GETTER_PATTERN = re.compile(
    r'get iotDownloadUrl\(\)\{.*?https://news\.rongyuan\.tech/iot_driver/.*?\}get vcredistx86DownloadUrl\(\)',
    re.DOTALL,
)

DEVICE_NOT_SUPPORTED_MODAL_PATTERN = re.compile(
    r'(?P<error>[A-Za-z_$][\w$]*)\.errorCode===(?P<enum>[A-Za-z_$][\w$]*)\.DEVICE_NOT_SUPPORTED\?'
    r'\((?P<state>[A-Za-z_$][\w$]*)\.isDeviceSupportedInNewDriver=!1,'
    r'(?P=state)\.showJumpToOldDriverModal=!0\):'
    r'\((?P=state)\.isDeviceSupportedInNewDriver=!0,'
    r'(?P=state)\.showJumpToOldDriverModal=!1\)'
)

UNGUARDED_DEVICE_NOT_SUPPORTED_MODAL_PATTERN = re.compile(
    r'[A-Za-z_$][\w$]*\.errorCode===[A-Za-z_$][\w$]*\.DEVICE_NOT_SUPPORTED\?'
    r'\([A-Za-z_$][\w$]*\.isDeviceSupportedInNewDriver=!1,'
    r'[A-Za-z_$][\w$]*\.showJumpToOldDriverModal=!0\):'
    r'\([A-Za-z_$][\w$]*\.isDeviceSupportedInNewDriver=!0,'
    r'[A-Za-z_$][\w$]*\.showJumpToOldDriverModal=!1\)'
)

COMPANY_MAPPING_ALLOWLIST_PATTERN = re.compile(
    r'!(?P<company_set>[A-Za-z_$][\w$]*)\.has\((?P<device>[A-Za-z_$][\w$]*)\.company\)&&'
    r'!(?P<display_set>[A-Za-z_$][\w$]*)\.has\((?P=device)\.displayName\)'
)

FOOTER_EXTERNAL_LINKS_RENDER_PATTERN = re.compile(
    r'children:![A-Za-z_$][\w$]*&&\((?P<condition>.*?)\)&&d\.(?P<jsx>jsxs?)\((?P<container>[A-Za-z_$][\w$]*),\{',
    re.DOTALL,
)

QUOTED_DEPENDENCY_PATTERN = re.compile(r'"([^"]+)"')

URL_PLACEHOLDER_REPLACEMENTS: tuple[tuple[str, str], ...] = (
    ("https://beian.miit.gov.cn/#/Integrated/index", "#"),
    ("https://qmk.top/gear-lab", "#"),
    ("https://iotdriver.qmk.top/", "#"),
    ("https://iotdriver.gearhub.top/", "#"),
    ("https://aka.ms/vs/17/release/vc_redist.x86.exe", "#"),
    ("https://aka.ms/vs/17/release/vc_redist.x64.exe", "#"),
    ("https://api3.rongyuan.tech:3816/api/v2", "/offline-disabled/api/v2"),
    ("https://api2.qmk.top:3816/api/v2", "/offline-disabled/api/v2"),
    ("https://api2.rongyuan.tech:3816/api/v2", "/offline-disabled/api/v2"),
    ("https://api3.rongyuan.tech:3816/download/bit_image_file", "/offline-disabled/download/bit_image_file"),
    ("https://api2.qmk.top:3816/download/bit_image_file", "/offline-disabled/download/bit_image_file"),
    ("https://api2.rongyuan.tech:3816/download", "/offline-disabled/download"),
    ("https://api.rongyuan.tech:3814/v1", "/offline-disabled/v1"),
    ("https://api2.qmk.top:3814/v1", "/offline-disabled/v1"),
)


def _iter_scan_files(site_root: Path, scan_files: Sequence[Path] | None) -> Iterable[Path]:
    if scan_files is None:
        candidates: Iterable[Path] = site_root.rglob("*")
    else:
        candidates = scan_files

    for file_path in candidates:
        if not file_path.is_file():
            continue
        if file_path.suffix.lower() not in PERMANENT_BLOCKED_SCAN_SUFFIXES:
            continue
        yield file_path


def resolve_main_bundle_path(site_root: Path) -> Path | None:
    js_dir = site_root / "js"
    index_html = site_root / "index.html"

    if index_html.exists():
        html = index_html.read_text(encoding="utf-8", errors="ignore")
        match = MAIN_BUNDLE_SRC_PATTERN.search(html)
        if match:
            candidate = js_dir / match.group("bundle")
            if candidate.exists():
                return candidate

    candidates = sorted(
        js_dir.glob("index.*.js"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not candidates:
        return None
    return candidates[0]


def _normalize_dependency_path(raw_dependency: str) -> str | None:
    normalized = raw_dependency.replace("\\\\", "/").replace("\\", "/")
    if normalized.startswith("./"):
        return f"js/{normalized[2:]}"
    if normalized.startswith("../"):
        return normalized[3:]
    if normalized.startswith("/"):
        return normalized[1:]
    if normalized:
        return normalized
    return None


def disable_ai_helper_lazy_import(content: str) -> tuple[str, bool, set[str]]:
    updated = content
    removed_paths: set[str] = set()
    changed = False

    if AI_HELPER_LAZY_IMPORT_EXACT in updated:
        updated = updated.replace(AI_HELPER_LAZY_IMPORT_EXACT, "Hoe=()=>null", 1)
        removed_paths.update({"js/0afe9811.js", "assets/css/AiFloat.db6806a6.css"})
        changed = True

    def _replace(match: re.Match[str]) -> str:
        for dependency in QUOTED_DEPENDENCY_PATTERN.findall(match.group("deps")):
            normalized = _normalize_dependency_path(dependency)
            if normalized is not None:
                removed_paths.add(normalized)
        return f"{match.group('var')}=()=>null"

    updated, replacements = AI_HELPER_LAZY_IMPORT_PATTERN.subn(_replace, updated, count=1)
    if replacements > 0:
        changed = True

    return updated, changed, removed_paths


def disable_ai_helper_floating_render(content: str) -> tuple[str, bool]:
    updated, changed = replace_text(
        content,
        '!v.isNoAIAssistant()&&d.jsx(y.Suspense,{fallback:d.jsx(d.Fragment,{}),children:d.jsx(Hoe,{deviceName:v.getCurrentDevice().deviceType.displayName??"",useProductionServer:!0,company:v.getCurrentDevice().deviceType.company,deviceType:v.getCurrentDevice().deviceType.type})})',
        "!1",
    )
    if changed:
        return updated, True

    updated, replacements = AI_HELPER_FLOATING_RENDER_PATTERN.subn("!1", content, count=1)
    return updated, replacements > 0


def neutralize_iot_download_getter(content: str) -> tuple[str, bool]:
    updated, changed = replace_text(
        content,
        'get iotDownloadUrl(){const e=this.getPlatform();return e?`https://news.rongyuan.tech/iot_driver/${e}/iot_manager_setup_v${e==="mac"?$_:Yd}.${e==="mac"?"dmg":"exe"}?${new Date().getTime()}`:void 0}',
        'get iotDownloadUrl(){return"#"}',
    )
    if changed:
        return updated, True

    updated, replacements = IOT_DOWNLOAD_GETTER_PATTERN.subn(
        'get iotDownloadUrl(){return"#"}get vcredistx86DownloadUrl()',
        content,
        count=1,
    )
    return updated, replacements > 0


def patch_device_not_supported_modal_flow(content: str) -> tuple[str, bool]:
    updated, changed = replace_text(
        content,
        'o.errorCode===$s.DEVICE_NOT_SUPPORTED?(v.isDeviceSupportedInNewDriver=!1,v.showJumpToOldDriverModal=!0):(v.isDeviceSupportedInNewDriver=!0,v.showJumpToOldDriverModal=!1)',
        'o.errorCode===$s.DEVICE_NOT_SUPPORTED?(v.isUseIotSDK?(v.isDeviceSupportedInNewDriver=!1,v.showJumpToOldDriverModal=!0):(v.isDeviceSupportedInNewDriver=!0,v.showJumpToOldDriverModal=!1)):(v.isDeviceSupportedInNewDriver=!0,v.showJumpToOldDriverModal=!1)',
    )
    if changed:
        return updated, True

    def _replace(match: re.Match[str]) -> str:
        error_var = match.group("error")
        enum_var = match.group("enum")
        state_var = match.group("state")
        return (
            f"{error_var}.errorCode==={enum_var}.DEVICE_NOT_SUPPORTED?"
            f"({state_var}.isUseIotSDK?"
            f"({state_var}.isDeviceSupportedInNewDriver=!1,{state_var}.showJumpToOldDriverModal=!0):"
            f"({state_var}.isDeviceSupportedInNewDriver=!0,{state_var}.showJumpToOldDriverModal=!1))"
            f":({state_var}.isDeviceSupportedInNewDriver=!0,{state_var}.showJumpToOldDriverModal=!1)"
        )

    updated, replacements = DEVICE_NOT_SUPPORTED_MODAL_PATTERN.subn(_replace, content, count=1)
    return updated, replacements > 0


def patch_company_mapping_allowlist(content: str) -> tuple[str, bool]:
    updated, changed = replace_text(
        content,
        '!n.has(u.company)&&!AT.has(u.displayName)',
        '(!n.has(u.company)||u.company==="EWEADNV")&&!AT.has(u.displayName)',
    )
    if changed:
        return updated, True

    def _replace(match: re.Match[str]) -> str:
        company_set = match.group("company_set")
        device_var = match.group("device")
        display_set = match.group("display_set")
        return (
            f"(!{company_set}.has({device_var}.company)||{device_var}.company===\"EWEADNV\")"
            f"&&!{display_set}.has({device_var}.displayName)"
        )

    updated, replacements = COMPANY_MAPPING_ALLOWLIST_PATTERN.subn(_replace, content, count=1)
    return updated, replacements > 0


def hide_external_footer_links_section(content: str) -> tuple[str, bool]:
    updated, changed = replace_text(content, "children:!vt&&(", "children:!1&&(", count=1)
    if changed:
        return updated, True

    def _replace(match: re.Match[str]) -> str:
        condition = match.group("condition")
        required_tokens = ("qmk.top", "gearhub.top", "localhost", "127.0.0.1")
        if not all(token in condition for token in required_tokens):
            return match.group(0)
        jsx_kind = match.group("jsx")
        container = match.group("container")
        return f"children:!1&&d.{jsx_kind}({container},{{"

    updated, replacements = FOOTER_EXTERNAL_LINKS_RENDER_PATTERN.subn(_replace, content, count=1)
    return updated, replacements > 0


def has_visible_external_footer_links(content: str) -> bool:
    for match in FOOTER_EXTERNAL_LINKS_RENDER_PATTERN.finditer(content):
        condition = match.group("condition")
        required_tokens = ("qmk.top", "gearhub.top", "localhost", "127.0.0.1")
        if all(token in condition for token in required_tokens):
            return True
    return False


def collect_reachable_runtime_files(site_root: Path) -> set[Path]:
    index_html = site_root / "index.html"
    if not index_html.exists():
        return set()

    base_url = "https://offline.local/"
    queue: deque[Path] = deque([index_html])
    seen_rel_paths: set[str] = set()
    reachable_files: set[Path] = set()

    while queue:
        file_path = queue.popleft()
        if not file_path.exists() or not file_path.is_file():
            continue

        rel_path = file_path.relative_to(site_root).as_posix()
        if rel_path in seen_rel_paths:
            continue

        seen_rel_paths.add(rel_path)
        reachable_files.add(file_path)

        suffix = file_path.suffix.lower()
        if suffix not in {".html", ".js", ".mjs", ".css"}:
            continue

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        file_url = urljoin(base_url, rel_path)

        refs: set[str] = set()
        if suffix == ".html":
            refs |= extract_html_refs(file_url, text)
        elif suffix in {".js", ".mjs"}:
            refs |= extract_js_refs(file_url, text)
        elif suffix == ".css":
            refs |= extract_css_refs(file_url, text)

        for ref in refs:
            local_target = to_local_path(site_root, clean_url(ref))
            if not local_target.exists() or not local_target.is_file():
                continue
            child_rel_path = local_target.relative_to(site_root).as_posix()
            if child_rel_path not in seen_rel_paths:
                queue.append(local_target)

    return reachable_files


def find_blocked_markers(
    site_root: Path,
    markers: Iterable[str],
    max_hits: int = 20,
    scan_files: Sequence[Path] | None = None,
) -> list[str]:
    hits: list[str] = []
    for file_path in _iter_scan_files(site_root, scan_files):
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        rel = file_path.relative_to(site_root).as_posix()
        for marker in markers:
            if marker in text:
                hits.append(f"{rel} -> {marker}")
                if len(hits) >= max_hits:
                    return hits

    return hits


def _host_matches_suffix(host: str, suffix: str) -> bool:
    return host == suffix or host.endswith("." + suffix)


def audit_external_url_hosts(
    site_root: Path,
    max_blocked_hits: int = 20,
    scan_files: Sequence[Path] | None = None,
) -> tuple[list[str], Counter[str]]:
    blocked_hits: list[str] = []
    unknown_hosts: Counter[str] = Counter()

    for file_path in _iter_scan_files(site_root, scan_files):
        text = file_path.read_text(encoding="utf-8", errors="ignore")
        rel = file_path.relative_to(site_root).as_posix()
        for raw_url in EXTERNAL_URL_RE.findall(text):
            host = (urlsplit(raw_url).hostname or "").lower()
            if not host:
                continue

            if host in {"127.0.0.1", "localhost"}:
                continue
            if host in BALANCED_ALLOWED_EXTERNAL_REFERENCE_HOSTS:
                continue

            if any(_host_matches_suffix(host, suffix) for suffix in BALANCED_BLOCKED_EXTERNAL_HOST_SUFFIXES):
                blocked_hits.append(f"{rel} -> {raw_url}")
                if len(blocked_hits) >= max_blocked_hits:
                    return blocked_hits, unknown_hosts
                continue

            unknown_hosts[host] += 1

    return blocked_hits, unknown_hosts


_CSP_META_TAG_RE = re.compile(
    r"<meta\s+[^>]*http-equiv=[\"']Content-Security-Policy[\"'][^>]*>",
    re.IGNORECASE,
)
_CSP_CONTENT_ATTR_RE = re.compile(r"content=([\"'])(.*?)\1", re.IGNORECASE | re.DOTALL)
_CSP_CONNECT_SRC_RE = re.compile(r"\bconnect-src\s+([^;]+)", re.IGNORECASE)


def validate_offline_connect_src(index_html: Path) -> list[str]:
    if not index_html.exists():
        return ["Missing index.html for CSP validation."]

    html = index_html.read_text(encoding="utf-8", errors="ignore")
    csp_tags = _CSP_META_TAG_RE.findall(html)
    if not csp_tags:
        return ["Missing CSP meta tag in index.html."]

    violations: list[str] = []
    connect_src_found = False

    for tag in csp_tags:
        content_match = _CSP_CONTENT_ATTR_RE.search(tag)
        if not content_match:
            violations.append("CSP meta tag is missing a content attribute.")
            continue

        csp_content = content_match.group(2)
        connect_match = _CSP_CONNECT_SRC_RE.search(csp_content)
        if not connect_match:
            violations.append("CSP policy is missing a connect-src directive.")
            continue

        connect_src_found = True
        tokens = [token for token in connect_match.group(1).split() if token]
        for token in tokens:
            if token not in OFFLINE_CONNECT_SRC_ALLOWED_TOKENS:
                violations.append(f"connect-src token not allowed: {token}")

    if not connect_src_found and not violations:
        violations.append("CSP policy is missing a connect-src directive.")

    return violations


def insert_before_main_bundle_script(html: str, tag: str) -> tuple[str, bool]:
    if tag in html:
        return html, False

    pattern = re.compile(r'(<script\s+type="module"\s+crossorigin\s+src="\./js/index\.[^"]+\.js"></script>)')
    updated, replacements = pattern.subn(f"        {tag}\n        \\1", html, count=1)
    if replacements > 0:
        return updated, True

    return html.replace("</head>", f"        {tag}\n    </head>", 1), True


def insert_after_main_bundle_script(html: str, tag: str) -> tuple[str, bool]:
    if tag in html:
        return html, False

    pattern = re.compile(r'(<script\s+type="module"\s+crossorigin\s+src="\./js/index\.[^"]+\.js"></script>)')
    updated, replacements = pattern.subn(f"\\1\n        {tag}", html, count=1)
    if replacements > 0:
        return updated, True

    return html.replace("</head>", f"        {tag}\n    </head>", 1), True


def apply_linux_patches(site_root: Path) -> list[str]:
    """Patch bundle to keep Linux on WebHID path by default."""
    patch_notes: list[str] = []
    index_file = resolve_main_bundle_path(site_root)
    if index_file is None:
        patch_notes.append("No index.*.js found; skipped Linux patching.")
        return patch_notes

    original = index_file.read_text(encoding="utf-8", errors="ignore")
    patched = original
    ai_removed_rel_paths: set[str] = set()

    patch_notes.append(f"Patching active runtime bundle: {index_file.name}.")

    patched, notes = apply_rules(patched, CORE_PATCH_RULES)
    patch_notes.extend(notes)

    patched, changed = patch_device_not_supported_modal_flow(patched)
    if changed:
        patch_notes.append("Patched DEVICE_NOT_SUPPORTED flow to suppress old-driver modal in WebHID mode.")

    patched, changed = patch_company_mapping_allowlist(patched)
    if changed:
        patch_notes.append("Patched device ID mapping to allow EWEADNV devices in web offline mode.")

    patched, changed = hide_external_footer_links_section(patched)
    if changed:
        patch_notes.append("Patched footer render to hide external website links in offline UI.")

    before_lazy = patched
    patched, changed, ai_removed_paths = disable_ai_helper_lazy_import(patched)
    if changed and patched != before_lazy:
        ai_removed_rel_paths.update(ai_removed_paths)
        patch_notes.append("Patched AI helper lazy import to no-op component.")

    patched, changed = disable_ai_helper_floating_render(patched)
    if changed:
        patch_notes.append("Patched AI helper floating button render path to disabled state.")

    before_links = patched
    patched = patched.replace("https://beian.miit.gov.cn/#/Integrated/index", "#")
    patched = patched.replace("https://qmk.top/gear-lab", "#")
    if patched != before_links:
        patch_notes.append("Patched footer link targets to local placeholders.")

    before_driver_links = patched
    patched = patched.replace(
        'oldDriverUrl=window.location.hostname.toLowerCase().includes("qmk")?"https://iotdriver.qmk.top/":(window.location.hostname.toLowerCase().includes("gearhub"),"https://iotdriver.gearhub.top/")',
        'oldDriverUrl="#"',
    )
    patched = patched.replace("https://iotdriver.qmk.top/", "#")
    patched = patched.replace("https://iotdriver.gearhub.top/", "#")
    patched, _ = neutralize_iot_download_getter(patched)
    patched = patched.replace("https://news.rongyuan.tech/iot_driver/", "#")
    patched = patched.replace(
        'get vcredistx86DownloadUrl(){return"https://aka.ms/vs/17/release/vc_redist.x86.exe"}',
        'get vcredistx86DownloadUrl(){return"#"}',
    )
    patched = patched.replace("https://aka.ms/vs/17/release/vc_redist.x86.exe", "#")
    patched = patched.replace(
        'get vcredistx64DownloadUrl(){return"https://aka.ms/vs/17/release/vc_redist.x64.exe"}',
        'get vcredistx64DownloadUrl(){return"#"}',
    )
    patched = patched.replace("https://aka.ms/vs/17/release/vc_redist.x64.exe", "#")
    if patched != before_driver_links:
        patch_notes.append("Patched remaining external driver/download URLs to local placeholders.")

    before_cloud_api_links = patched
    for old_value, new_value in URL_PLACEHOLDER_REPLACEMENTS:
        if "/offline-disabled" not in new_value:
            continue
        patched = patched.replace(old_value, new_value)
    if patched != before_cloud_api_links:
        patch_notes.append("Patched cloud API base URLs to offline-local placeholders.")

    before_theme_rewrites = patched
    for old_color, new_color in THEME_COLOR_REPLACEMENTS:
        patched = patched.replace(old_color, new_color)
    if patched != before_theme_rewrites:
        patch_notes.append("Patched legacy hardcoded palette colors to theme variables.")

    patched, changed = strip_topnav_branding(patched)
    if changed:
        patch_notes.append("Patched logged-in top-left branding logo block to hidden state.")

    patched, changed = disable_footer_factory_reset_button(patched)
    if changed:
        patch_notes.append("Disabled footer factory-reset button in main runtime shell.")

    if UNGUARDED_DEVICE_NOT_SUPPORTED_MODAL_PATTERN.search(patched):
        raise RuntimeError(
            "Linux patch enforcement failed; old-driver modal still opens in WebHID flow (missing isUseIotSDK guard)."
        )

    if has_visible_external_footer_links(patched):
        raise RuntimeError("Linux patch enforcement failed; footer external-link section is still visible.")

    if patched != original:
        index_file.write_text(patched, encoding="utf-8")
    else:
        patch_notes.append("Main runtime bundle already satisfied Linux WebHID/offline patch rules.")

    patch_notes.extend(patch_more_tab_controls(site_root))

    patch_notes.extend(ensure_theme_assets(site_root))

    index_html = site_root / "index.html"
    if index_html.exists():
        html_original = index_html.read_text(encoding="utf-8", errors="ignore")
        csp_meta = f'<meta http-equiv="Content-Security-Policy" content="{OFFLINE_CSP_CONTENT}" />'
        html_patched = html_original
        html_changed = False

        if 'http-equiv="Content-Security-Policy"' in html_patched:
            html_patched, replacements = re.subn(
                r"<meta\s+http-equiv=[\"']Content-Security-Policy[\"'][^>]*>",
                csp_meta,
                html_patched,
                count=1,
                flags=re.IGNORECASE,
            )
            html_changed = html_changed or replacements > 0
        else:
            viewport_pattern = re.compile(
                r"(<meta[^>]*name=[\"']viewport[\"'][^>]*>\s*)",
                re.IGNORECASE,
            )
            html_patched, replacements = viewport_pattern.subn(
                r"\1        " + csp_meta + "\n",
                html_patched,
                count=1,
            )
            html_changed = html_changed or replacements > 0
            if replacements == 0:
                html_patched = html_patched.replace("</head>", f"        {csp_meta}\n    </head>", 1)
                html_changed = True

        theme_css_tag = '<link rel="stylesheet" href="./assets/css/theme-overrides.css" />'
        offline_guard_tag = '<script src="./js/offline-runtime-guard.js"></script>'
        theme_init_tag = '<script src="./js/theme-init.js"></script>'
        theme_runtime_adapter_tag = '<script defer src="./js/theme-runtime-adapter.js"></script>'
        theme_switcher_tag = '<script defer src="./js/theme-switcher.js"></script>'

        html_patched, inserted = insert_before_main_bundle_script(html_patched, offline_guard_tag)
        html_changed = html_changed or inserted

        html_patched, inserted = insert_before_main_bundle_script(html_patched, theme_css_tag)
        html_changed = html_changed or inserted

        html_patched, inserted = insert_before_main_bundle_script(html_patched, theme_init_tag)
        html_changed = html_changed or inserted

        html_patched, inserted = insert_after_main_bundle_script(html_patched, theme_runtime_adapter_tag)
        html_changed = html_changed or inserted

        html_patched, inserted = insert_after_main_bundle_script(html_patched, theme_switcher_tag)
        html_changed = html_changed or inserted

        if html_patched != html_original:
            index_html.write_text(html_patched, encoding="utf-8")
            if html_changed:
                patch_notes.append("Ensured offline CSP + theme bootstrap/switcher hooks in index.html.")

    removed_rel_paths = {
        "js/0afe9811.js",
        "assets/css/AiFloat.db6806a6.css",
    }
    removed_rel_paths.update(ai_removed_rel_paths)

    removed_paths = [site_root / rel_path for rel_path in sorted(removed_rel_paths)]
    removed_count = 0
    for path in removed_paths:
        if path.exists():
            path.unlink()
            removed_count += 1
    if removed_count:
        patch_notes.append("Removed AI helper floating-widget bundle files from offline site.")

    reachable_scan_files = tuple(sorted(collect_reachable_runtime_files(site_root), key=lambda path: str(path)))
    scan_targets: Sequence[Path] | None = reachable_scan_files if reachable_scan_files else None
    if reachable_scan_files:
        patch_notes.append(
            f"Scoped marker and egress audits to {len(reachable_scan_files)} reachable runtime files."
        )

    blocked_hits = find_blocked_markers(site_root, PERMANENT_BLOCKED_MARKERS, scan_files=scan_targets)
    if blocked_hits:
        preview = "\n".join(blocked_hits)
        raise RuntimeError(
            "Permanent-strip enforcement failed; blocked AI/link markers remain in runtime files:\n" + preview
        )
    patch_notes.append("Verified AI helper and external links are permanently stripped from runtime files.")

    csp_violations = validate_offline_connect_src(index_html)
    if csp_violations:
        preview = "\n".join(csp_violations)
        raise RuntimeError("Offline CSP validation failed:\n" + preview)
    patch_notes.append("Verified CSP connect-src remains localhost-only for offline mode.")

    blocked_external_urls, unknown_external_hosts = audit_external_url_hosts(site_root, scan_files=scan_targets)
    if blocked_external_urls:
        preview = "\n".join(blocked_external_urls)
        raise RuntimeError("Balanced egress audit failed; blocked remote hosts remain:\n" + preview)

    if unknown_external_hosts:
        observed = ", ".join(
            f"{host} ({count})" for host, count in unknown_external_hosts.most_common(5)
        )
        patch_notes.append(
            "Balanced egress audit found review-only external reference hosts: "
            + observed
            + "."
        )
    else:
        patch_notes.append("Balanced egress audit found no non-allowlisted external hosts in runtime files.")

    return patch_notes
