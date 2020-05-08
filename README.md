# My-blockchain-model

林逸舟

Blockchain python 简单服务器使用说明：

语言：python
数据库：MySQL (两个存储表格：blockchain本身、网络中的其他节点地址)
框架：Flask

Blockchain表格：索引，时间戳，上一块区块的哈希值，本区块的工作证明。
Neighbors表格：其他节点的地址


服务器开始运行：Blockchain类初始化，连接数据库，获得当前链长度(chainlength)。
节点存储：nodes(set)
链存储：chain(list)
开放交易信息存储：current_transactions(list)

'/mine' GET请求：服务器将当前开放交易信息封存入区块中，开始挖矿，挖矿过程中，每一百次循环，向中心节点发送'/getblock' GET请求，如中心节点已经有封存完成的区块，将其取来进行工作证明有效性验证并检测交易信息是否与自己收到的相同，如其证明有效，将其连接到本节点区块链尾部，存入数据库。如在挖矿过程中中心节点未有封存完成的区块，挖矿完成后，向中心节点发送'/minedblock' POST请求, 如中心节点已经有封存完成的区块，将其取来进行工作证明有效性验证并检测交易信息是否与自己收到的相同，如其证明有效，将其连接到本节点区块链尾部，存入数据库, 如中心节点仍未有已经有封存完成的区块，中心节点将收到的新区块存储，发送给余下其他节点，挖矿完成的节点获得奖金，并将其存入本区块链。

‘/chain’ GET请求：服务器从数据库中调取本节点存储的整条区块链数据，并返回给前端

'/transactions/new' POST 请求：服务器将收到的交易信息，存入blockchain. current_transactions(list)中，待开始挖矿时，将其封存入新区块中。

'/nodes/register' POST请求：服务器将收到的新节点地址，存入数据库中

'/nodes/resolve' GET请求：服务器调取数据库中其他节点地址，向其他节点发送‘/chain’ GET请求，调取其他节点存储的区块链，将本节点区块链替换为网络当中的最长有效链。
