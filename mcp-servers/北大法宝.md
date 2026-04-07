# 北大法宝 MCP 接入教程

1. 访问：mcp.pkulaw.com

2. 注册/登陆账号，进入法宝MCP控制台，点击应用管理，点击 + 创建应用，输入应用名称，点击创建应用

   ![image-20260321204224752](./assets/image-20260321204224752.png)

3. 点击密钥管理，生成token认证，保存好token

   ![image-20260321204427065](./assets/image-20260321204427065.png)

4. MCP服务购买，新用户可免费使用一个月部分服务

   ![image-20260321204558454](./assets/image-20260321204558454.png)

5. 进入MCP Playground查看要使用的服务的连接信息

   ![image-20260321205729495](./assets/image-20260321205729495.png)

6. JSON配置格式示例：

   ```
   {
     "mcpServers": {
       "pkulaw-law-search": {
         "name": "检索法律法规-语义"
         "type": "streamable-http",
         "streamable": true,
         "url": "https://apim-gateway.pkulaw.com/mcp-law-search-service",
         "headers": {
           "Authorization": "Bearer c9c3435a-df96-3606-ae42-ea475cc79546"
         },
         "disabled": false
       }
     }
   }
   ```

   ⚠️ 注意：示例中的 `{{YOUR_ACCESS_TOKEN}}` 是占位符，请替换为您在应用详情页生成的真实 Token

7. 把刚才保存的token替换JSON配置示例中的`{{YOUR_ACCESS_TOKEN}}`，然后将整个JSON配置复制进入Claude Code或Codex等agentic AI工具中，让agent自己安装，安装成功后重启claude：

   ![image-20260321210049255](./assets/image-20260321210049255.png)

   ![image-20260321210527191](./assets/image-20260321210527191.png)

8. 其他问题参考法宝官方MCP服务接入指南（https://mcp.pkulaw.com/docs?doc=mcp-integration）
