# Nuclei-tools

![image](https://github.com/hughink/Nuclei-tools/assets/105833193/81717727-fc48-47f4-8308-0f78f8716986)

## 用来管理自己为数不多的 Nuclei-poc

### 一、POC的增删改查

#### 1、增加

当未选中行时，在编辑器中默认为增加状态，可以在yaml 编辑器中编写自己的nuclei测试脚本，编写结束后，点击保存并命名（添加文件内容和文件名重复检测）

![image](https://github.com/hughink/Nuclei-tools/assets/105833193/a60928f5-7dfd-493b-98f7-58c15d81af70)


#### 2、删除

![image](https://github.com/hughink/Nuclei-tools/assets/105833193/6cb66e56-4aa3-46c0-922f-b1a37ba8b3db)


#### 3、修改

选中某个脚本进行修改保存

![image](https://github.com/hughink/Nuclei-tools/assets/105833193/5a35f3a8-0a6a-47d1-bf47-161c16d481f6)


#### 4、查询

具备全局搜索功能，可以搜索yaml 文件中的任意关键词

![image](https://github.com/hughink/Nuclei-tools/assets/105833193/09162ac8-c34f-4a84-80c6-0674d092f6e2)

或者使用 AND 或 OR 搜索筛选两个关键词

![image](https://github.com/hughink/Nuclei-tools/assets/105833193/48ff1fcb-ee40-4bcc-99d5-5fd0774424b5)


### 二、POC 的扫描

#### 1、单个poc, 一个或者多个目标的扫描

通过鼠标单击选中某一行（即表示选中某一个POC），在空白输入框内输入一个或者多个目标，点击运行后进行 单个poc, 一个或者多个目标的扫描。（细节勾选框为 nuclei的 --dresp 参数）

![image](https://github.com/hughink/Nuclei-tools/assets/105833193/8b0a28e4-9af5-4cb8-9181-4bed07015d80)


#### 2、多个poc, 一个或者多个目标的扫描

通过全局搜索，将搜索筛选结果作为要扫描使用的poc，在空白输入框内输入一个或者多个目标，点击运行后进行 单个poc, 一个或者多个目标的扫描。（细节勾选框为 nuclei的 --dresp 参数）

![image](https://github.com/hughink/Nuclei-tools/assets/105833193/0faec794-0505-437b-a69d-52890ec9b9f4)



