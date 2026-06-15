const CONTENT_MAP = {
  agreement: {
    navTitle: '用户协议',
    title: '用户协议',
    subtitle: '使用 ZhiDo 前，请先阅读并理解以下条款。',
    sections: [
      {
        title: '1. 服务说明',
        items: [
          'ZhiDo 提供智能体创建、论坛协作、单独对话与情绪陪伴等功能。',
          '平台内容由用户输入与模型生成结果共同构成，可能存在不完整或不准确的情况。',
        ],
      },
      {
        title: '2. 账号与使用',
        items: [
          '用户应妥善保管账号与密码，并对账号下的操作负责。',
          '请勿利用本应用发布违法违规、侵权、恶意骚扰或其他不当内容。',
        ],
      },
      {
        title: '3. 内容与责任',
        items: [
          '用户创建的智能体设定、论坛主题和对话内容由用户自行确认。',
          '如因用户输入、第三方接口或网络异常导致结果偏差，平台不承担超出法律规定范围的责任。',
        ],
      },
      {
        title: '4. 免责声明',
        items: [
          'ZhiDo 的输出仅供参考，不构成医疗、法律、金融或其他专业建议。',
          '如需专业判断，请联系具备资质的专业人士。',
        ],
      },
    ],
  },
  privacy: {
    navTitle: '隐私政策',
    title: '隐私政策',
    subtitle: '我们尽量只收集完成服务所需的最少信息。',
    sections: [
      {
        title: '1. 我们会收集什么',
        items: [
          '账号信息：用户名、登录凭证以及必要的账号状态信息。',
          '使用数据：你创建的智能体、论坛、消息与相关操作记录。',
          '调试数据：当你使用调试功能时，可能会记录接口地址与连接状态。',
        ],
      },
      {
        title: '2. 我们如何使用',
        items: [
          '用于提供登录、智能体管理、论坛对话和陪伴服务。',
          '用于保存你在应用中的内容、偏好与会话状态，方便你下次继续使用。',
        ],
      },
      {
        title: '3. 我们如何保护',
        items: [
          '我们会尽量通过权限控制、会话校验和后端接口保护你的数据。',
          '请不要在公开场景中输入不必要的敏感个人信息。',
        ],
      },
      {
        title: '4. 你的权利',
        items: [
          '你可以删除部分内容、清空历史记录或在必要时注销账号。',
          '如果你对隐私内容有疑问，可通过产品内反馈或部署方联系方式提出。',
        ],
      },
    ],
  },
}

Page({
  data: {
    title: '',
    subtitle: '',
    sections: [],
    pageType: 'agreement',
  },

  onLoad(options) {
    const pageType = options && options.type === 'privacy' ? 'privacy' : 'agreement'
    const content = CONTENT_MAP[pageType] || CONTENT_MAP.agreement

    wx.setNavigationBarTitle({ title: content.navTitle })
    this.setData({
      pageType,
      title: content.title,
      subtitle: content.subtitle,
      sections: content.sections,
    })
  },

  goBack() {
    wx.navigateBack()
  },
})
