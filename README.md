在nginx源码上添加注释。

nginx源码中的注释内容统一实用/* xxx */风格，为了以示区分我加入的注释都会采用//风格。
我加入的注释内容主要以中文为主，部分需要借助更复杂的图文说明的片段，我在注释中将加入文章链接。

目录docs是我新增加的目录，主要用于存放难以在注释中简易说明的内容。

当前同步nginx版本为[1.15.6](http://nginx.org/download/nginx-1.15.6.tar.gz)。

毫无疑问nginx是一个十分优秀的开源项目，它拥有许多优秀的设计。
但在二次开发的工作过程中也发现了nginx项目中也有缺点，造成了理解和开发上的困难。明显的问题如下：

- 某些局部复杂度过高，经常出现一些很长的函数。（具体数据还在分析中）
- 变量名命名方式过于随意
    - 全局变量含义有时不够清晰（好在全局变量不算太多）
    - 局部变量名称无法明确表达含义，太过简短了，当出现多个相同类型的变量时往往难以区分。
- 源码中缺少注释，对于核心逻辑与一些复杂的逻辑注释都少得可怜，理解困难。
- 部分设计过于复杂，接口名称相似度太高，又没有对应的文档/说明支撑，二次开发中容易误用。

