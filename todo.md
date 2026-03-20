# TODO

## 后续按需事项

- 补更多厂家 profile
  - 前提：拿到对应厂家文档
  - 落点：`edgefusion/adapters/modbus/profiles/vendors/`

- 按现场需要补充协议支持
  - 候选：MQTT / CAN / HTTP
  - 原则：先定设备模型，再补协议适配层、传输协议层、物理连接层

- 持续保持手工接入主导
  - 不扩重型自动发现体系
  - 新接入优先补 profile，不改业务层分支
