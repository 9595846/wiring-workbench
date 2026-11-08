"""Local stdio MCP tools for saved wiring projects; no firmware or hardware writes."""
import sys,os,json,uuid
from pathlib import Path
ROOT=Path(__file__).resolve().parent
# Workspace development fallback; portable installs should use their own venv.
try:import mcp
except ImportError:
 vendor=ROOT.parent/'oled_preview/vendor'
 for part in (vendor,vendor/'win32',vendor/'win32/lib',vendor/'Pythonwin'):sys.path.insert(0,str(part))
 if sys.platform=='win32' and (vendor/'pywin32_system32').exists():dll_handle=os.add_dll_directory(str(vendor/'pywin32_system32'))
from mcp.server.fastmcp import FastMCP
import project_store as store
import global_library
mcp=FastMCP('模块接线工作台')
@mcp.tool()
def list_projects()->list:
    """列出本工作台磁盘上已保存项目及当前 revision。网页未保存内容不可见。"""
    return store.listing()
@mcp.tool()
def read_project(project_id:str)->dict:
    """读取完整项目（模块、针脚、线、标注、库快照）和 revision。"""
    return store.read(project_id)
@mcp.tool()
def create_project(title:str)->dict:
    """创建独立空白项目，复制全局模板快照，不修改任何现有项目。"""
    lib=global_library.read_library()['modules'];pkg=store.engine('new',title=title,library=lib);ident='project_'+uuid.uuid4().hex
    return dict(store.write(ident,pkg,0,'mcp'),project_id=ident)
@mcp.tool()
def update_project(project_id:str,package:dict,expected_revision:int)->dict:
    """替换完整接线项目，必须带最新 revision。校验后自动保留修改前恢复点；不修改固件。"""
    return store.write(project_id,package,expected_revision,'mcp','MCP 完整更新前自动恢复点')
@mcp.tool()
def edit_project(project_id:str,operations:list[dict],expected_revision:int)->dict:
    """原子执行最多50项编辑。先用 get_edit_help 获取格式；失败不保存，成功有自动恢复点和新 revision。"""
    return store.edit(project_id,operations,expected_revision)
@mcp.tool()
def get_edit_help()->dict:
    """返回编辑操作说明。对象ID应先从 read_project 获取，不按名称猜ID。"""
    return {'operations':{
      'set_power_display':{'type':'set_power_display','mode':'compact'},
      'rename_project':{'type':'rename_project','title':'新图纸'},
      'add_module':{'type':'add_module','template_id':'当前项目 library 中的 id','x':100,'y':100},
      'add_custom_module':{'type':'add_custom_module','name':'我的模块','kind':'输入','pins':['VCC','GND','SIG'],'x':100,'y':100},
      'move_module':{'type':'move_module','id':'模块ID','x':200,'y':100},
      'update_pin':{'type':'update_pin','module':'模块ID','pin':'针脚ID','changes':{'name':'SCL','voltage':'3.3V','electrical':{'type':'open_drain','required':False,'pullup':'unknown'}}},
      'connect':{'type':'connect','a':{'module':'模块ID','pin':'针脚ID'},'b':{'node':'网络标记ID'},'purpose':'用途'},
      'update_wire':{'type':'update_wire','id':'导线ID','changes':{'purpose':'OLED SCL','color':'#257c69'}},
      'lock_wire':{'type':'lock_wire','id':'导线ID','locked':True},
      'tidy_routes':{'type':'tidy_routes','ids':['导线ID'],'reset_manual':False},
      'add_net':{'type':'add_net','name':'GND','x':100,'y':100,'attach':{'module':'模块ID','pin':'针脚ID'}},
      'add_annotation':{'type':'add_annotation','kind':'note','text':'讲解说明','x':100,'y':100},
      'delete_object':{'type':'delete_object','kind':'modules','id':'对象ID','cascade':False}},
      'rules':['电压/电气属性未知时保留未知，不自动猜测。','同名网络标记会相连。删除关联导线需明确 cascade=true。','网页端重新打开项目可读到 MCP 已保存修改；旧网页直接保存会触发修订号冲突。']}
@mcp.tool()
def check_project(project_id:str)->dict:
    """复用网页静态连接检查规则，列出风险、待确认和未知信息。不是实物验收。"""
    return store.engine('check',package=store.read(project_id)['package'])
@mcp.tool()
def preview_project(project_id:str)->dict:
    """导出当前已保存项目SVG简图和检查结果；复用网页走线模型，返回本地文件路径。"""
    current=store.read(project_id);result=store.engine('preview',package=current['package']);folder=ROOT/'mcp_previews';folder.mkdir(exist_ok=True);name=folder/(project_id+'-v'+str(current['revision'])+'.svg');name.write_text(result['svg'],encoding='utf-8');return {'revision':current['revision'],'path':str(name.resolve()),'checks':result['checks'],'note':result['note']}
@mcp.tool()
def list_restore_points(project_id:str)->list:
    """列出项目的手动与自动恢复点。"""
    return store.checkpoints(project_id)
@mcp.tool()
def create_restore_point(project_id:str,expected_revision:int,label:str='MCP 手动恢复点')->dict:
    """为当前已保存内容创建恢复点，不增加项目修订号。"""
    return store.create_checkpoint(project_id,expected_revision,label)
@mcp.tool()
def restore_project(project_id:str,checkpoint_id:str,expected_revision:int)->dict:
    """恢复指定旧内容，先保存当前内容的恢复点，再生成新修订号；保留历史记录。"""
    return store.restore(project_id,checkpoint_id,expected_revision)
@mcp.tool()
def read_global_library()->dict:
    """读取全局模板及版本摘要；不更新旧项目，也不发布全局模板。"""
    return global_library.read_library()
if __name__=='__main__':mcp.run()
