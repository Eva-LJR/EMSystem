import schemas

print("--- 检查 schemas 根目录下的可用类 ---")
root_attributes = [x for x in dir(schemas) if not x.startswith('_')]
print(root_attributes)

if "Token" in root_attributes:
    print("结果：Token 确实在根目录下，这不可能报错。")
else:
    print("结果：Token 不在根目录下！")
    if "UserInDB" in root_attributes:
        print("--- 检查 Token 是否不小心缩进成了 UserInDB 的内部类 ---")
        user_attrs = dir(schemas.UserInDB)
        if "Token" in user_attrs:
            print("🚨 抓到了！Token 变成了 UserInDB 的内部类！请检查 schemas.py 中的缩进！")