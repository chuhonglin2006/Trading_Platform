"""验证学号是否匹配"""
from datetime import datetime


def check_student_id(student_id:str) -> bool:
    """
    验证学号是否匹配
    :param student_id:学号
    :return:匹配结果
    """
    if not student_id.isdigit() or len(student_id) != 9:
        return False
    current_year = datetime.now().year % 100
    min_year = current_year - 2
    admission_year = int(student_id[:2])
    return min_year <= admission_year <= current_year
