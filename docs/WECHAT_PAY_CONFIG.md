# 微信支付配置说明

## 配置项说明

### 1. 缓存配置（第 37-38 行）

```bash
CACHE_CULL_FREQUENCY=3    # 缓存清理频率（当缓存条目达到最大值时，清理多少条目）
CACHE_TIMEOUT=300         # 缓存超时时间（秒），300秒 = 5分钟
```

**说明**：
- `CACHE_CULL_FREQUENCY`：当缓存达到最大条目数时，每次清理 3 个条目
- `CACHE_TIMEOUT`：缓存数据在 300 秒（5分钟）后过期

**如何设置**：
- 一般使用默认值即可
- 如果系统内存较小，可以减小 `CACHE_MAX_ENTRIES`
- 如果需要更频繁的缓存更新，可以减小 `CACHE_TIMEOUT`

---

### 2. 微信支付 V3 API 配置

#### WECHAT_KEY_PATH（私钥文件路径）⭐ **重要**

**用途**：用于 JSAPI 支付签名（必需）

**文件**：`apiclient_key.pem`

**如何获取**：
1. 登录 [微信支付商户平台](https://pay.weixin.qq.com/)
2. 进入 **账户中心** → **API安全** → **API证书**
3. 点击 **下载证书**
4. 解压后找到 `apiclient_key.pem` 文件
5. 将文件保存到服务器安全位置

**配置示例**：
```bash
WECHAT_KEY_PATH=/path/to/apiclient_key.pem
# Windows 示例
WECHAT_KEY_PATH=D:\certificates\apiclient_key.pem
# 或相对路径（相对于项目根目录）
WECHAT_KEY_PATH=./certificates/apiclient_key.pem
```

**安全提示**：
- ⚠️ **私钥文件非常重要，绝对不能泄露！**
- 不要将私钥文件提交到 Git 仓库
- 建议将证书文件放在项目目录外，或使用环境变量
- 设置文件权限为仅所有者可读（Linux: `chmod 600 apiclient_key.pem`）

---

#### WECHAT_CERT_SERIAL_NO（证书序列号）⭐ **必需**

**用途**：用于微信支付 V3 API 身份验证

**如何获取**：
1. 从下载的证书文件中提取
2. 使用命令：`openssl x509 -in apiclient_cert.pem -noout -serial`
3. 或者从证书文件内容中查找 `serial=` 字段

**配置示例**：
```bash
WECHAT_CERT_SERIAL_NO=444F4864EA9B34415...
```

---

#### WECHAT_APIV3_KEY（API v3 密钥）⭐ **必需**

**用途**：用于微信支付 V3 API 回调数据解密

**如何获取**：
1. 登录 [微信支付商户平台](https://pay.weixin.qq.com/)
2. 进入 **账户中心** → **API安全** → **API密钥**
3. 点击 **设置APIv3密钥**
4. 设置一个 32 位的密钥（建议使用随机生成器）

**配置示例**：
```bash
WECHAT_APIV3_KEY=MIIEvwIBADANBgkqhkiG9w0BAQE...
```

**安全提示**：
- ⚠️ **API v3 密钥非常重要，绝对不能泄露！**
- 不要将密钥提交到 Git 仓库
- 定期更换密钥以提高安全性

---

#### WECHAT_CERT_DIR（平台证书缓存目录）

**用途**：用于缓存微信支付平台证书（SDK 自动管理）

**如何设置**：
1. 创建一个空目录用于缓存证书
2. 首次使用确保目录为空
3. SDK 会自动下载并缓存平台证书

**配置示例**：
```bash
WECHAT_CERT_DIR=./cert
# 或绝对路径
WECHAT_CERT_DIR=/path/to/cert
```

**注意事项**：
- 首次使用确保目录为空
- SDK 会自动管理证书的下载和更新
- 建议使用相对路径，便于部署

---

## 完整配置示例

```bash
# 微信小程序配置
WECHAT_APPID=wx23fedab0e057b533                    # 小程序 AppID
WECHAT_APPSECRET=your_app_secret                   # 小程序 AppSecret

# 微信支付 V3 API 配置
WECHAT_MCHID=1722164814                            # 商户号
WECHAT_MCH_ID=1722164814                           # 商户号（别名）

# 支付回调地址（必须是公网 HTTPS URL）
WECHAT_NOTIFY_URL=https://yourdomain.com/api/order/callback

# 私钥文件路径（必需，用于支付签名）
WECHAT_KEY_PATH=/path/to/apiclient_key.pem

# V3 API 配置
WECHAT_CERT_SERIAL_NO=你的证书序列号              # 证书序列号
WECHAT_APIV3_KEY=你的APIv3密钥                    # API v3 密钥
WECHAT_CERT_DIR=./cert                             # 平台证书缓存目录
```

---

## 获取步骤详解

### 步骤 1：登录微信支付商户平台
访问：https://pay.weixin.qq.com/

### 步骤 2：进入 API 安全设置
1. 登录后，点击顶部菜单 **账户中心**
2. 在左侧菜单选择 **API安全**
3. 找到 **API证书** 部分

### 步骤 3：下载证书
1. 点击 **下载证书** 按钮
2. 输入商户平台的登录密码进行验证
3. 下载 ZIP 压缩包

### 步骤 4：解压并获取文件
解压后你会看到以下文件：
- `apiclient_cert.pem` - 证书文件（用于退款等操作）
- `apiclient_key.pem` - **私钥文件（用于支付签名，必需）**
- `apiclient_cert.p12` - PKCS12 格式证书（可选）

### 步骤 5：配置到项目
1. 将 `apiclient_key.pem` 文件放到服务器安全位置
2. 在 `.env` 文件中配置 `WECHAT_KEY_PATH` 指向该文件
3. 确保文件路径正确且文件可读

---

## 注意事项

1. **私钥文件安全**：
   - 绝对不能泄露给他人
   - 不要提交到代码仓库
   - 定期更换证书（建议每年更换一次）

2. **文件路径**：
   - 可以使用绝对路径或相对路径
   - 相对路径是相对于 Django 项目的根目录（`mall-server/`）
   - Windows 路径使用反斜杠或正斜杠都可以

3. **权限设置**（Linux/Mac）：
   ```bash
   chmod 600 apiclient_key.pem    # 仅所有者可读
   chmod 644 apiclient_cert.pem   # 证书文件可以稍宽松
   ```

4. **测试环境**：
   - 开发环境可以使用沙箱环境测试
   - 生产环境必须使用真实证书

---

## 常见问题

**Q: 证书文件找不到怎么办？**
A: 检查文件路径是否正确，确保使用绝对路径或正确的相对路径。

**Q: 提示"权限被拒绝"？**
A: 检查文件权限，确保应用有读取权限。

**Q: 可以使用相对路径吗？**
A: 可以，但建议使用绝对路径更安全可靠。

**Q: 证书过期了怎么办？**
A: 重新下载新证书，更新 `WECHAT_KEY_PATH` 配置。

