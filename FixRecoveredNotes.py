from trilium_py.client import ETAPI
import sys
import os
import logging
import datetime
import traceback
import argparse
from dotenv import load_dotenv
import json


load_dotenv()  # 加载 .env 文件中的变量到环境变量

# 日志配置：同时输出到控制台和文件
LOG_FILE = "duplicate_log.md"  
# 创建 logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# 防止重复添加 handler
if not logger.handlers:
    # 控制台 handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    logger.addHandler(console_handler)

    # 文件 handler
    file_handler = logging.FileHandler(LOG_FILE, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    logger.addHandler(file_handler)
    
def backup_database(ea):
    """
    触发 Trilium 数据库备份，备份名称使用当前时间戳。
    备份文件将保存在 Trilium 的 backup 目录下，文件名格式为 backup-YYYYMMDD_HHMMSS.db。
    """
    try:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = "BeforeAction_" + timestamp
        result = ea.backup(backup_name)
        logger.info(f"数据库备份成功，备份名称: {backup_name}，返回信息: {result}")
    except Exception as e:
        logger.error(f"数据库备份失败: {e}")

def get_default_content_for_type(note_type, mime=None):
    """根据笔记类型返回一个默认的有效内容"""
    if note_type == 'mindMap':
        return '{}'  # 空 JSON 对象
    elif note_type == 'render':
        return '{}'
    elif note_type == 'relationMap':
        return '[]'
    elif note_type == 'code' and mime:
        # 根据 MIME 类型返回合适的注释
        if mime in ['application/javascript', 'text/javascript']:
            return '// 此笔记已由恢复脚本创建'
        elif mime == 'text/html':
            return '<!-- 此笔记已由恢复脚本创建 -->'
        elif mime == 'text/css':
            return '/* 此笔记已由恢复脚本创建 */'
        else:
            return ''  # 其他 code 类型可能不需要内容
    elif note_type == 'text':
        return '<p>此笔记已由恢复脚本创建</p>'
    else:
        # 对于未知类型，尝试空字符串（可能失败，但日志会记录）
        logger.warning(f"未知笔记类型 {note_type}，使用空内容，可能失败")
        return ''
# 在 duplicate_subtree 函数入口处添加 visited 集合并传递
def duplicate_subtree(ea, source_note_id, new_parent_id=None, copy_attributes=True, copy_attachments=True, visited=None):
    if visited is None:
        visited = set()
    
    # 检测循环引用
    if source_note_id in visited:
        logger.error(f"检测到循环引用，笔记 ID: {source_note_id}，跳过")
        return None
    
    visited.add(source_note_id)
    # ... 后续逻辑不变

# def duplicate_subtree(ea, source_note_id, new_parent_id=None, copy_attributes=True, copy_attachments=True):
    """
    递归复制以 source_note_id 为根的整个子树，并挂载到 new_parent_id 下。
    如果 new_parent_id 为 None，则复制到原笔记的第一个父节点（保持原层级）。
    支持复制属性、附件，并处理不同笔记类型。
    返回新复制的根笔记ID。
    """
    # 获取原笔记完整信息
    source_note = ea.get_note(source_note_id)
    title = source_note['title']
    note_type = source_note.get('type', 'text')
    mime = source_note.get('mime', 'text/html')
    is_protected = source_note.get('isProtected', False)

    if is_protected:
        logger.warning(f"笔记 {title} (ID: {source_note_id}) 受保护，跳过复制")
        return None

    # 获取原笔记内容（仅对 text 或 code 等直接内容有效，image/file 内容通过附件处理）
    # content = ea.get_note_content(source_note_id) if note_type in ['text', 'code'] else ''
    # 获取原笔记内容（仅对需要内容的类型有效）
    content = ''
    try:
        if note_type in ['text', 'code', 'mindMap', 'render', 'relationMap']:
            content = ea.get_note_content(source_note_id)
    except Exception as e:
        logger.warning(f"获取笔记 {title} 内容失败: {e}，将使用默认内容")
        content = ''


    # --- 处理空内容或添加标记 ---
    if note_type not in ['image', 'file']:
        # 判断是否为空
        is_empty = not content or (isinstance(content, str) and content.strip() == '')
        # 对于其他类型，如果内容为空，设置默认内容
        if is_empty:
            content = get_default_content_for_type(note_type, mime)
            logger.info(f"笔记 {title} 内容为空，使用默认内容")


    # 确定新笔记的父节点
    if new_parent_id is None:
        parent_ids = source_note.get('parentNoteIds', ['root'])
        parent_id = parent_ids[0] if parent_ids else 'root'
    else:
        parent_id = new_parent_id
            # 根据笔记类型创建新笔记
    try:
        if note_type == 'image':
            attachments = ea.get_attachments(source_note_id)
            if not attachments:
                logger.warning(f"图片笔记 {title} 没有附件，创建空白图片笔记")
                new_note = ea.create_image_note(parentNoteId=parent_id, title=title, image_file=None)
            else:
                att = attachments[0]
                att_content = ea.get_attachment_content(att['attachmentId'])
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(att.get('title', ''))[1]) as tmp:
                    tmp.write(att_content)
                    tmp_path = tmp.name
                new_note = ea.create_image_note(parentNoteId=parent_id, title=title, image_file=tmp_path)
                os.unlink(tmp_path)
        elif note_type == 'file':
            attachments = ea.get_attachments(source_note_id)
            if not attachments:
                logger.warning(f"文件笔记 {title} 没有附件，创建空白文件笔记")
                new_note = ea.create_note(parentNoteId=parent_id, title=title, type='file', content='')
            else:
                att = attachments[0]
                att_content = ea.get_attachment_content(att['attachmentId'])
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(att.get('title', ''))[1]) as tmp:
                    tmp.write(att_content)
                    tmp_path = tmp.name
                # 创建空白文件笔记，再上传附件
                new_note = ea.create_note(parentNoteId=parent_id, title=title, type='file', content='')
                new_note_id = new_note['note']['noteId']
                ea.create_attachment(ownerId=new_note_id, file_path=tmp_path)
                os.unlink(tmp_path)
                # 重新获取笔记信息以包含附件
                new_note = ea.get_note(new_note_id)
        else:
            # 其他类型：text, code, mindMap, render 等
            create_kwargs = {
                'parentNoteId': parent_id,
                'title': title,
                'type': note_type,
                'content': content
            }
            if mime and note_type in ['code', 'mindMap', 'render', 'relationMap']:
                create_kwargs['mime'] = mime
            new_note = ea.create_note(**create_kwargs)
        
        # 检查返回值
        if not isinstance(new_note, dict):
            logger.error(f"创建笔记返回非字典类型: {new_note}")
            return None
        if 'note' not in new_note:
            logger.error(f"创建笔记返回缺少 'note' 键: {new_note}")
            return None
        new_note_id = new_note['note']['noteId']
        logger.info(f"✅ 复制笔记: '{title}' (原ID: {source_note_id}) -> 新ID: {new_note_id} 在父节点 {parent_id}")

        # 添加标签 "已修复recovered错误"
        try:
            ea.create_attribute(
                noteId=new_note_id,
                type='label',
                name='已修复recovered错误',
                value='',
                isInheritable=False
            )
            logger.debug(f"为笔记 {new_note_id} 添加标签 '已修复recovered错误'")
        except Exception as e:
            logger.error(f"为笔记 {new_note_id} 添加标签失败: {e}")

    except Exception as e:
        logger.error(f"创建笔记 {title} 时发生异常: {e}", exc_info=True)
        return None

    # 复制属性（只复制属于当前笔记本身的属性）
    if copy_attributes:
        attrs = source_note.get('attributes', [])
        for attr in attrs:
            if attr.get('noteId') != source_note_id:
                continue
            try:
                ea.create_attribute(
                    noteId=new_note_id,
                    type=attr['type'],
                    name=attr['name'],
                    value=attr.get('value', ''),
                    isInheritable=attr.get('isInheritable', False)
                )
                logger.debug(f"复制属性 {attr['name']} 到新笔记 {new_note_id}")
            except Exception as e:
                logger.error(f"复制属性 {attr.get('name')} 失败: {e}")

    # 复制其他附件（对于非 image/file 笔记）
    if copy_attachments and note_type not in ['image', 'file']:
        attachments = ea.get_attachments(source_note_id)
        for att in attachments:
            try:
                att_content = ea.get_attachment_content(att['attachmentId'])
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(att.get('title', ''))[1]) as tmp:
                    tmp.write(att_content)
                    tmp_path = tmp.name
                ea.create_attachment(ownerId=new_note_id, file_path=tmp_path)
                os.unlink(tmp_path)
                logger.debug(f"复制附件 {att.get('title')} 到新笔记 {new_note_id}")
            except Exception as e:
                logger.error(f"复制附件失败: {e}")

    # 递归子笔记
    child_ids = source_note.get('childNoteIds', [])
    for child_id in child_ids:
        duplicate_subtree(ea, child_id, new_note_id, copy_attributes, copy_attachments)

    return new_note_id

def find_notes_by_title_prefix(ea,prefix):

    search_pattern = f"note.title ^= '{prefix}'"  # 只匹配开头

    res = ea.search_note(
        search=prefix,
        fastSearch=False,
        orderBy=["title"],
        limit=1000  # 如果笔记较多，可以适当扩大 limit
    )
    return res

def duplicate_recovered_notes(ea,prefix,label_name):
    
    res = find_notes_by_title_prefix(ea,prefix)
    logger.debug(res)

    logger.info(f"正在检索带有 {prefix} 的笔记: ")

    notes_found = res.get('results',[])
    logger.info(f"找到 {len(notes_found)} 个匹配的笔记。")

    if len(notes_found) == 0:
        logger.info(f"检索式 {prefix} 未检索到相应笔记")
        
    else:
        
        for x in notes_found:
            note_id = x['noteId']
            original_title = x['title']
            isProtected = x['isProtected']
            # 检查是否已有副本
            attrs = x.get('attributes', [])
            # logger.info(f"{original_title}   {attrs}")
            has_copy_label = any(attr.get('type') == 'label' and attr.get('name') == label_name  for attr in attrs)

            if has_copy_label:
                logger.info(f"笔记 {original_title} (ID: {note_id}) 已有标签 '{label_name}'，视为已复制，跳过")
                continue
           
            try:
                # 获取原笔记的元数据信息（用于获取它的父节点、笔记类型等信息）
                note_meta = ea.get_note(note_id)
                logger.info(f"笔记标题信息 {original_title} ")
                duplicate_subtree(ea, note_id)         

            except Exception as e:
                logger.error(f"复制笔记 '{original_title}' (ID: {note_id}) 时发生错误: {e}")
                logger.error(traceback.format_exc())  # 打印完整堆栈
        

def delete_recovered_notes(ea, prefix,label_name):
    """
    删除所有标题以 prefix 开头的原始笔记（内容不含标记“已修复recovered错误”），及其子树。
    如果内容包含标记，则视为复制品，跳过删除。
    """
    result = find_notes_by_title_prefix(ea, prefix)
    notes = result.get('results', [])
    
    deleted_count = 0

    for note in notes:
        logging.debug(note)
        note_id = note['noteId']
        title = note['title']

        attrs = note.get('attributes', [])

        has_label = any(attr.get('type') == 'label' and attr.get('name') == label_name for attr in attrs)
        
        if has_label:
            logger.info(f"笔记 {title} (ID: {note_id}) 包含标签 '{label_name}'，视为复制品，跳过删除")
            continue


        # 无标记，属于原始笔记，执行删除
        logger.info(f"准备删除原始笔记: {title} (ID: {note_id})")
        try:
            ea.delete_note(note_id)
            logger.info(f"✅ 已删除原始笔记及其子树: {title}")
            deleted_count += 1
            # break
        except Exception as e:
            logger.error(f"删除笔记 {title} 失败: {e}")

    logger.info(f"删除完成，共删除 {deleted_count} 个原始笔记及其子树")


def clean_recovered_notes(ea, prefix,label_name):
    """
    删除所有内容包含标记“已修复recovered错误”且标题与任何原始 recovered 笔记相同的笔记及其子树。
    """
    
    # 1. 获取所有原始 recovered 笔记的标题集合
    res_original = find_notes_by_title_prefix(ea, prefix)
    original_notes = res_original.get('results', [])
    original_titles = {note['title'] for note in original_notes}
    logger.info(f"原始 recovered 笔记标题集合: {original_titles}")
    
    if not original_titles:
        logger.info("没有原始 recovered 笔记，无需清理")
        return
    
    # 3. 遍历候选笔记，删除符合条件的
    deleted_count = 0
    for title  in original_titles:
        try:
                
            res = find_notes_by_title_prefix(ea,title)
            candidates = res.get('results', [])
            for note in candidates:
                    note_id = note['noteId']
                    note_title = note['title']
                    attrs = note.get('attributes', [])
                    has_label = any(attr.get('type') == 'label' and attr.get('name') == label_name for attr in attrs)
                    if has_label:
                        logger.info(f"准备删除复制品笔记: {note_title} (ID: {note_id})")
                        try:
                            ea.delete_note(note_id)
                            logger.info(f"✅ 已删除笔记及其子树: {note_title}")
                            deleted_count += 1
                        except Exception as e:
                            logger.error(f"删除笔记 {note_title} 失败: {e}")
        except Exception as e:
            logger.error(f"搜索标题 '{title}' 时出错: {e}", exc_info=True)
    
    logger.info(f"清理完成，共删除 {deleted_count} 个笔记（及其子树）")
    
def check_only_recovered(ea, prefix):
    """
    仅检查模式：检索标题包含 prefix 的笔记，如果有，则在当天 TODO 中添加一条提醒（如果尚未存在）。
    """
    res = find_notes_by_title_prefix(ea, prefix)
    notes = res.get('results', [])

    if notes:
        logger.info(f"找到 {len(notes)} 个匹配笔记，准备添加 TODO 提醒")
        for note in notes:
            title = note['title']
            logger.info(f"笔记标题{title}")
        todo_text = "检查 recovered note"
        today = datetime.datetime.now().strftime("%Y-%m-%d")
        try:
            day_content = ea.get_day_note(today)
            if todo_text not in day_content:
                ea.add_todo(todo_text)
                logger.info(f"✅ 已添加 TODO: {todo_text}")
            else:
                logger.info("TODO 已存在，跳过添加")
        except Exception as e:
            logger.error(f"添加 TODO 失败: {e}")
    else:
        logger.info("没有匹配笔记，不添加 TODO")

def main(server_url, token, prefix,
         copy_mode=False, delete_mode=False, clean_mode=False, check_only=False,
         no_backup=False,label_name = '已修复recovered错误'):
    ea = ETAPI(server_url, token)
    res = find_notes_by_title_prefix(ea, prefix)

    if res.get('results') and not no_backup and not check_only:
        backup_database(ea)

    if check_only:
        logger.info("执行检查模式：检索笔记并添加 TODO 提醒（不修改笔记）")
        check_only_recovered(ea, prefix)
    elif clean_mode:
        logger.info("执行清理模式：删除标题匹配且含标签的笔记")
        clean_recovered_notes(ea, prefix,label_name)
    elif delete_mode:
        logger.info("执行删除模式：删除所有找到的原始笔记及其子树")
        delete_recovered_notes(ea, prefix,label_name)
    elif copy_mode:
        logger.info("执行复制模式：复制所有找到的笔记及其子树")
        duplicate_recovered_notes(ea, prefix,label_name)
    else:
        # 理论上不会到达这里，因为 check_only 覆盖了其他情况
        check_only_recovered(ea, prefix)

    logger.info("操作完成。")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="处理标题带特定关键词的笔记：检查、复制、删除或清理")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--copy", action="store_true", help="复制模式：复制所有找到的笔记及其子树")
    group.add_argument("--delete", action="store_true", help="删除模式：删除找到的原始笔记及其子树")
    group.add_argument("--clean", action="store_true", help="清理模式：删除标题相同且含标签的复制笔记及其子树")
    parser.add_argument("--no-backup", action="store_true", help="跳过自动备份")
    args = parser.parse_args()

    # 原有环境变量读取保持不变
    SERVER_URL = os.environ.get("TRILIUM_SERVER", "http://localhost:8080")
    TOKEN = os.environ.get("TRILIUM_TOKEN", "")
    PREFIX = os.environ.get("TITLE_PREFIX", "recovered")

    if not TOKEN:
        logger.error("未提供 Trilium ETAPI token。请设置环境变量 TRILIUM_TOKEN。")
        sys.exit(1)

    # 确定模式：默认检查模式
    copy_mode = args.copy
    delete_mode = args.delete
    clean_mode = args.clean
    check_only = not (copy_mode or delete_mode or clean_mode)
    label_name = '已修复recovered错误'

    main(SERVER_URL, TOKEN, PREFIX,
         copy_mode=copy_mode,
         delete_mode=delete_mode,
         clean_mode=clean_mode,
         check_only=check_only,
         no_backup=args.no_backup,
         label_name = label_name)
