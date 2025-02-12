import re
import os
import random
import string

def generate_random_id():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=6))

def parse_skill_block(input_text):
    skills = {}
    current_skill = None
    current_content = []
    lines = input_text.strip().split('\n')
    for line in lines:
        # Deteksi awal deklarasi skill (dengan atau tanpa condition)
        skill_match = re.match(r'skill\s+(\w+)(?:\s+condition\s+(.+))?:', line)
        if skill_match:
            # Jika sudah ada skill sebelumnya, simpan isinya
            if current_skill is not None:
                if isinstance(current_skill, dict):
                    skills[current_skill['name']] = {
                        'condition': current_skill['condition'],
                        'content': '\n'.join(current_content)
                    }
                else:
                    skills[current_skill] = '\n'.join(current_content)
            name = skill_match.group(1)
            condition = skill_match.group(2)
            current_skill = {'name': name, 'condition': condition} if condition else name
            current_content = []
        else:
            current_content.append(line)
    if current_skill is not None:
        if isinstance(current_skill, dict):
            skills[current_skill['name']] = {
                'condition': current_skill['condition'],
                'content': '\n'.join(current_content)
            }
        else:
            skills[current_skill] = '\n'.join(current_content)
    return skills

def process_block(lines, base_indent):
    """
    Fungsi rekursif untuk memproses baris–baris (lines) dengan indentasi minimal base_indent.
    Menghasilkan struktur data berupa:
      {
        "conditions": [list kondisi dalam blok ini],
        "skills": [list aksi (string) dalam blok ini],
        "sub_skills": { id: struktur blok anak }
      }
    """
    conditions = []
    actions = []
    sub_skills = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        stripped = line.lstrip()
        current_indent = len(line) - len(stripped)
        if current_indent < base_indent:
            break
        # --- Deteksi if condition ---
        if stripped.startswith("if ") and " castinstead:" in stripped:
            cond_match = re.match(r'if\s+(.+?)\s+castinstead:', stripped)
            if cond_match:
                cond = cond_match.group(1)
                # Buat ID unik untuk blok if ini
                if_id = f"condition_{generate_random_id()}"
                i += 1
                # Kumpulkan baris–baris untuk blok if (dengan indentasi lebih dari current_indent)
                if_block_lines = []
                while i < len(lines):
                    next_line = lines[i]
                    if not next_line.strip():
                        i += 1
                        continue
                    next_indent = len(next_line) - len(next_line.lstrip())
                    if next_indent <= current_indent:
                        break
                    if_block_lines.append(next_line)
                    i += 1
                # Proses blok if secara rekursif
                if_structure = process_block(if_block_lines, current_indent + 2)
                sub_skills[if_id] = if_structure
                conditions.append(f"{cond} castinstead {if_id}")
                # --- Deteksi optional else pada blok yang sama ---
                if i < len(lines):
                    next_line = lines[i]
                    if next_line.lstrip().startswith("else:"):
                        else_id = f"else_condition_{generate_random_id()}"
                        i += 1  # lewati baris "else:"
                        else_block_lines = []
                        while i < len(lines):
                            if not lines[i].strip():
                                i += 1
                                continue
                            next_indent = len(lines[i]) - len(lines[i].lstrip())
                            if next_indent <= current_indent:
                                break
                            else_block_lines.append(lines[i])
                            i += 1
                        else_structure = process_block(else_block_lines, current_indent + 2)
                        sub_skills[else_id] = else_structure
                        conditions.append(f"{cond} orelsecast {else_id}")
            else:
                i += 1
        # --- Deteksi loop ---
        elif stripped.startswith("loop ") and stripped.endswith(":"):
            loop_match = re.match(r'loop\s+(\d+):', stripped)
            if loop_match:
                count = int(loop_match.group(1))
                i += 1
                if i < len(lines):
                    action_line = lines[i].strip()
                    for j in range(1, count + 1):
                        processed_action = action_line
                        for math_expr in re.findall(r'<index[^>]*>', action_line):
                            expr = math_expr.strip('<>').replace('index', str(j))
                            try:
                                result = eval(expr)
                            except Exception:
                                result = expr
                            processed_action = processed_action.replace(math_expr, str(result))
                        actions.append(processed_action)
                    i += 1
                else:
                    i += 1
            else:
                i += 1
        else:
            # Jika baris biasa (aksi)
            actions.append(stripped)
            i += 1
    return {"conditions": conditions, "skills": actions, "sub_skills": sub_skills}

def format_structure(name, structure, indent=""):
    """
    Mengonversi struktur blok (dictionary) menjadi string berformat YAML.
    Jika 'name' diberikan, maka akan dicetak sebagai header block.
    """
    lines = []
    if name:
        lines.append(f"{name}:")
        inner_indent = "  "
    else:
        inner_indent = indent
    if structure["conditions"]:
        lines.append(f"{inner_indent}Conditions:")
        for cond in structure["conditions"]:
            lines.append(f"{inner_indent}- {cond}")
    lines.append(f"{inner_indent}Skills:")
    for skill in structure["skills"]:
        lines.append(f"{inner_indent}- {skill}")
    # Cetak blok-blok anak (sub_skills) secara terpisah
    for sub_id, sub_struct in structure["sub_skills"].items():
        lines.append("")
        sub_lines = format_structure(sub_id, sub_struct, indent="  ")
        lines.extend(sub_lines.splitlines())
    return "\n".join(lines)

def process_skill_content(content, main_condition=None, indent_level=0):
    """
    Mengonversi isi skill (DSL) menjadi output YAML.
    Jika ada main_condition, kondisi tersebut ditambahkan ke awal list conditions.
    """
    lines = content.split('\n')
    structure = process_block(lines, indent_level)
    if main_condition:
        structure["conditions"].insert(0, main_condition)
    return format_structure(None, structure)

def convert_files():
    script_dir = 'script'
    result_dir = 'result'

    if not os.path.exists(result_dir):
        os.makedirs(result_dir)

    output = []

    for filename in os.listdir(script_dir):
        if filename.endswith('.mms'):
            with open(os.path.join(script_dir, filename), 'r') as f:
                content = f.read()

            skills = parse_skill_block(content)

            for skill_name, skill_data in skills.items():
                result = []
                result.append(f"{skill_name}:")
                if isinstance(skill_data, dict):
                    processed_content = process_skill_content(skill_data['content'], skill_data['condition'])
                else:
                    processed_content = process_skill_content(skill_data)
                result.append(processed_content)
                output.append('\n'.join(result))

    with open(os.path.join(result_dir, 'skill.yml'), 'w') as f:
        f.write('\n'.join(output))

if __name__ == "__main__":
    convert_files()
