// /**
//  * Video Vault API - Serverless版本
//  * 直接操作OBS，无需Flask后端
//  */
// import {
//   uploadVideoToOBS,
//   checkVideoStatus,
//   getVideoDownloadURL,
//   listProcessedVideos,
//   getAuditLog,
//   deleteVideo,
//   checkOBSConfig
// } from './obs-client'

// export const videoAPI = {
//   /**
//    * 健康检查（检查OBS连接）
//    */
//   async healthCheck() {
//     try {
//       const isOk = await checkOBSConfig()
//       return {
//         status: isOk ? 'ok' : 'error',
//         mode: 'serverless',
//         timestamp: new Date().toISOString()
//       }
//     } catch (error) {
//       return {
//         status: 'error',
//         mode: 'serverless',
//         error: error.message,
//         timestamp: new Date().toISOString()
//       }
//     }
//   },

//   /**
//    * 上传视频（直接上传到OBS）
//    * @param {File} file - 视频文件
//    * @param {Function} onProgress - 进度回调 (percent, transferred, total, seconds)
//    */
//   async uploadVideo(file, onProgress) {
//     try {
//       const result = await uploadVideoToOBS(file, onProgress)

//       return {
//         success: true,
//         video_id: result.videoId,
//         object_key: result.objectKey,
//         message: '视频已上传到OBS，云函数正在自动处理...',
//         etag: result.etag
//       }
//     } catch (error) {
//       console.error('上传视频失败:', error)
//       throw new Error(`上传失败: ${error.message}`)
//     }
//   },

//   /**
//    * 检查视频处理状态
//    * @param {string} videoId - 视频ID
//    */
//   async getVideoStatus(videoId) {
//     try {
//       return await checkVideoStatus(videoId)
//     } catch (error) {
//       console.error('查询状态失败:', error)
//       return { status: 'error', error: error.message }
//     }
//   },

//   /**
//    * 获取视频列表（从OBS读取）
//    * @param {Object} params - 查询参数（暂不使用）
//    */
//   async getVideos(params = {}) {
//     try {
//       const videos = await listProcessedVideos(params.limit || 100)

//       // 转换为前端需要的格式
//       const formattedVideos = videos.map(v => ({
//         video_id: v.videoId,
//         title: v.filename || v.videoId,
//         filename: `${v.videoId}_sanitized.mp4`,
//         status: 'completed',
//         size: v.size,
//         created_at: v.lastModified,
//         download_url: null  // 需要时动态生成
//       }))

//       return {
//         videos: formattedVideos,
//         total: formattedVideos.length
//       }
//     } catch (error) {
//       console.error('获取视频列表失败:', error)
//       return { videos: [], total: 0, error: error.message }
//     }
//   },

//   /**
//    * 获取视频详情
//    * @param {string} videoId - 视频ID
//    */
//   async getVideoDetail(videoId) {
//     try {
//       // 并行查询状态和审计日志
//       const [status, auditLog] = await Promise.all([
//         checkVideoStatus(videoId),
//         getAuditLog(videoId)
//       ])

//       return {
//         video_id: videoId,
//         status: status.status,
//         size: status.size,
//         last_modified: status.lastModified,
//         audit_log: auditLog,
//         sensitive_count: auditLog?.total_detections || 0,
//         detections: auditLog?.detections || []
//       }
//     } catch (error) {
//       console.error('获取视频详情失败:', error)
//       throw new Error(`获取详情失败: ${error.message}`)
//     }
//   },

//   /**
//    * 获取视频下载URL
//    * @param {string} videoId - 视频ID
//    * @returns {Promise<string>} 下载URL
//    */
//   async downloadVideo(videoId) {
//     try {
//       return await getVideoDownloadURL(videoId)
//     } catch (error) {
//       console.error('获取下载链接失败:', error)
//       throw new Error(`获取下载链接失败: ${error.message}`)
//     }
//   },

//   /**
//    * 删除视频
//    * @param {string} videoId - 视频ID
//    */
//   async deleteVideo(videoId) {
//     try {
//       await deleteVideo(videoId)
//       return { success: true, message: '视频已删除' }
//     } catch (error) {
//       console.error('删除视频失败:', error)
//       throw new Error(`删除失败: ${error.message}`)
//     }
//   },

//   /**
//    * 获取审计日志
//    * @param {Object} params - 查询参数 {video_id, days}
//    */
//   async getAuditLogs(params = {}) {
//     try {
//       if (params.video_id) {
//         // 获取单个视频的审计日志
//         const log = await getAuditLog(params.video_id)
//         return {
//           logs: log?.detections || [],
//           total: log?.detections?.length || 0
//         }
//       } else {
//         // 获取所有视频的审计日志
//         const videos = await listProcessedVideos()
//         const allLogs = []

//         // 并行获取所有审计日志
//         const logPromises = videos.map(v => getAuditLog(v.videoId))
//         const logs = await Promise.all(logPromises)

//         logs.forEach((log, index) => {
//           if (log && log.detections) {
//             const videoId = videos[index].videoId
//             const detections = log.detections.map(d => ({
//               ...d,
//               video_id: videoId,
//               video_title: videos[index].filename
//             }))
//             allLogs.push(...detections)
//           }
//         })

//         // 按时间排序
//         allLogs.sort((a, b) => {
//           const timeA = a.timestamp || ''
//           const timeB = b.timestamp || ''
//           return timeB.localeCompare(timeA)
//         })

//         return {
//           logs: allLogs,
//           total: allLogs.length
//         }
//       }
//     } catch (error) {
//       console.error('获取审计日志失败:', error)
//       return { logs: [], total: 0, error: error.message }
//     }
//   },

//   /**
//    * 获取审计统计
//    * @param {number} days - 统计天数（serverless模式下忽略）
//    */
//   async getAuditStats(days = 7) {
//     try {
//       const videos = await listProcessedVideos()
//       const allDetections = []
//       const typeStats = {}

//       // 获取所有审计日志
//       const logPromises = videos.map(v => getAuditLog(v.videoId))
//       const logs = await Promise.all(logPromises)

//       logs.forEach(log => {
//         if (log && log.detections) {
//           allDetections.push(...log.detections)

//           // 统计各类型数量
//           log.detections.forEach(d => {
//             const type = d.type || 'unknown'
//             typeStats[type] = (typeStats[type] || 0) + 1
//           })
//         }
//       })

//       return {
//         total_detections: allDetections.length,
//         by_type: typeStats,
//         period_days: 0  // Serverless模式不区分时间段
//       }
//     } catch (error) {
//       console.error('获取审计统计失败:', error)
//       return {
//         total_detections: 0,
//         by_type: {},
//         period_days: 0,
//         error: error.message
//       }
//     }
//   },

//   /**
//    * 获取仪表盘数据
//    */
//   async getDashboard() {
//     try {
//       const videos = await listProcessedVideos()
//       const allDetections = []
//       let highRiskVideos = 0

//       // 获取所有审计日志
//       const logPromises = videos.map(v => getAuditLog(v.videoId))
//       const logs = await Promise.all(logPromises)

//       const recentActivity = []

//       logs.forEach((log, index) => {
//         if (log && log.detections) {
//           const videoId = videos[index].videoId
//           const detectionCount = log.detections.length

//           allDetections.push(...log.detections)

//           if (detectionCount >= 5) {
//             highRiskVideos++
//           }

//           // 添加最近活动（每个视频取前3条）
//           log.detections.slice(0, 3).forEach(d => {
//             recentActivity.push({
//               video_id: videoId,
//               video_title: videos[index].filename,
//               sensitive_type: d.type,
//               timestamp: d.timestamp,
//               confidence: d.confidence,
//               text: (d.text || '').substring(0, 50)
//             })
//           })
//         }
//       })

//       // 按时间排序最近活动
//       recentActivity.sort((a, b) => {
//         return (b.timestamp || '').localeCompare(a.timestamp || '')
//       })

//       return {
//         total_videos: videos.length,
//         processing_videos: 0,  // Serverless模式无法实时获取
//         completed_videos: videos.length,
//         total_sensitive_detections: allDetections.length,
//         high_risk_videos: highRiskVideos,
//         recent_activity: recentActivity.slice(0, 10)
//       }
//     } catch (error) {
//       console.error('获取仪表盘数据失败:', error)
//       return {
//         total_videos: 0,
//         processing_videos: 0,
//         completed_videos: 0,
//         total_sensitive_detections: 0,
//         high_risk_videos: 0,
//         recent_activity: [],
//         error: error.message
//       }
//     }
//   },

//   /**
//    * AI对话 - 通过华为云SDK直接调用函数
//    * @param {string} message - 用户消息
//    */
//   async aiChat(message) {
//     try {
//       // 动态导入 function-caller
//       const { invokeAIAgent } = await import('../utils/function-caller')

//       const result = await invokeAIAgent('chat', message)

//       // result 应该是 {response: "...", timestamp: "..."}
//       if (result && result.response) {
//         return {
//           response: result.response,
//           timestamp: result.timestamp || new Date().toISOString()
//         }
//       }

//       throw new Error('返回结果格式错误')
//     } catch (error) {
//       console.error('AI对话失败:', error)
//       throw new Error(`AI对话失败: ${error.message}`)
//     }
//   },

//   /**
//    * 重置AI对话 - 通过华为云SDK直接调用函数
//    */
//   async aiReset() {
//     try {
//       // 动态导入 function-caller
//       const { invokeAIAgent } = await import('../utils/function-caller')

//       const result = await invokeAIAgent('reset', '')

//       return {
//         message: result.message || '对话已重置',
//         success: true
//       }
//     } catch (error) {
//       console.error('重置对话失败:', error)
//       throw new Error(`重置失败: ${error.message}`)
//     }
//   }
// }

/**
 * Video Vault API - Serverless版本（修复版）
 * 主要修复：timestamp 排序、审计日志处理
 */
import {
  uploadVideoToOBS,
  checkVideoStatus,
  getVideoDownloadURL,
  listProcessedVideos,
  getAuditLog,
  deleteVideo,
  checkOBSConfig
} from './obs-client'

export const videoAPI = {
  // ... healthCheck, uploadVideo, getVideoStatus, getVideos, getVideoDetail 保持不变 ...

  async healthCheck() {
    try {
      const isOk = await checkOBSConfig()
      return { status: isOk ? 'ok' : 'error', mode: 'serverless', timestamp: new Date().toISOString() }
    } catch (error) {
      return { status: 'error', mode: 'serverless', error: error.message, timestamp: new Date().toISOString() }
    }
  },

  async uploadVideo(file, onProgress) {
    try {
      const result = await uploadVideoToOBS(file, onProgress)
      return { success: true, video_id: result.videoId, object_key: result.objectKey, message: '视频已上传到OBS，云函数正在自动处理...', etag: result.etag }
    } catch (error) {
      console.error('上传视频失败:', error)
      throw new Error(`上传失败: ${error.message}`)
    }
  },

  async getVideoStatus(videoId) {
    try {
      return await checkVideoStatus(videoId)
    } catch (error) {
      console.error('查询状态失败:', error)
      return { status: 'error', error: error.message }
    }
  },

  async getVideos(params = {}) {
    try {
      const videos = await listProcessedVideos(params.limit || 100)
      const formattedVideos = videos.map(v => ({
        video_id: v.videoId, title: v.filename || v.videoId, filename: `${v.videoId}_sanitized.mp4`,
        status: 'completed', size: v.size, created_at: v.lastModified, download_url: null
      }))
      return { videos: formattedVideos, total: formattedVideos.length }
    } catch (error) {
      console.error('获取视频列表失败:', error)
      return { videos: [], total: 0, error: error.message }
    }
  },

  async getVideoDetail(videoId) {
    try {
      const [status, auditLog] = await Promise.all([checkVideoStatus(videoId), getAuditLog(videoId)])
      return {
        video_id: videoId, status: status.status, size: status.size, last_modified: status.lastModified,
        audit_log: auditLog, sensitive_count: auditLog?.total_detections || 0, detections: auditLog?.detections || []
      }
    } catch (error) {
      console.error('获取视频详情失败:', error)
      throw new Error(`获取详情失败: ${error.message}`)
    }
  },

  async downloadVideo(videoId) {
    try {
      return await getVideoDownloadURL(videoId)
    } catch (error) {
      console.error('获取下载链接失败:', error)
      throw new Error(`获取下载链接失败: ${error.message}`)
    }
  },

  async deleteVideo(videoId) {
    try {
      await deleteVideo(videoId)
      return { success: true, message: '视频已删除' }
    } catch (error) {
      console.error('删除视频失败:', error)
      throw new Error(`删除失败: ${error.message}`)
    }
  },

  /**
   * 获取审计日志 - 修复版
   */
  async getAuditLogs(params = {}) {
    try {
      if (params.video_id) {
        const log = await getAuditLog(params.video_id)
        return { logs: log?.detections || [], total: log?.detections?.length || 0 }
      }

      const videos = await listProcessedVideos()
      const allLogs = []

      const logPromises = videos.map(v => getAuditLog(v.videoId))
      const logs = await Promise.all(logPromises)

      logs.forEach((log, index) => {
        if (log && log.detections && Array.isArray(log.detections)) {
          const videoId = videos[index].videoId
          const detections = log.detections.map(d => ({
            ...d,
            video_id: videoId,
            video_title: videos[index].filename || videoId
          }))
          allLogs.push(...detections)
        }
      })

      // ✅ 修复：timestamp 可能是数字，统一转换后排序
      allLogs.sort((a, b) => {
        const timeA = typeof a.timestamp === 'number' ? a.timestamp : parseFloat(a.timestamp) || 0
        const timeB = typeof b.timestamp === 'number' ? b.timestamp : parseFloat(b.timestamp) || 0
        return timeB - timeA
      })

      console.log('[video.js] getAuditLogs 返回:', allLogs.length, '条记录')
      return { logs: allLogs, total: allLogs.length }
    } catch (error) {
      console.error('获取审计日志失败:', error)
      return { logs: [], total: 0, error: error.message }
    }
  },

  /**
   * 获取审计统计 - 修复版
   */
  async getAuditStats(days = 7) {
    try {
      const videos = await listProcessedVideos()
      const allDetections = []
      const typeStats = {}

      const logPromises = videos.map(v => getAuditLog(v.videoId))
      const logs = await Promise.all(logPromises)

      logs.forEach(log => {
        if (log && log.detections && Array.isArray(log.detections)) {
          allDetections.push(...log.detections)
          log.detections.forEach(d => {
            const type = d.type || 'unknown'
            typeStats[type] = (typeStats[type] || 0) + 1
          })
        }
      })

      console.log('[video.js] getAuditStats 返回:', allDetections.length, '条检测')
      return { total_detections: allDetections.length, by_type: typeStats, period_days: 0 }
    } catch (error) {
      console.error('获取审计统计失败:', error)
      return { total_detections: 0, by_type: {}, period_days: 0, error: error.message }
    }
  },

  /**
   * 获取仪表盘数据 - 修复版
   */
  async getDashboard() {
    try {
      const videos = await listProcessedVideos()
      const allDetections = []
      let highRiskVideos = 0
      const recentActivity = []

      const logPromises = videos.map(v => getAuditLog(v.videoId))
      const logs = await Promise.all(logPromises)

      logs.forEach((log, index) => {
        if (log && log.detections && Array.isArray(log.detections)) {
          const videoId = videos[index].videoId
          const detectionCount = log.detections.length

          allDetections.push(...log.detections)

          if (detectionCount >= 5) {
            highRiskVideos++
          }

          log.detections.slice(0, 3).forEach(d => {
            recentActivity.push({
              video_id: videoId,
              video_title: videos[index].filename || videoId,
              sensitive_type: d.type,
              timestamp: d.timestamp,
              confidence: d.confidence,
              text: (d.text || '').substring(0, 50)
            })
          })
        }
      })

      // ✅ 修复：timestamp 可能是数字，不能用 localeCompare
      recentActivity.sort((a, b) => {
        const timeA = typeof a.timestamp === 'number' ? a.timestamp : parseFloat(a.timestamp) || 0
        const timeB = typeof b.timestamp === 'number' ? b.timestamp : parseFloat(b.timestamp) || 0
        return timeB - timeA
      })

      return {
        total_videos: videos.length,
        processing_videos: 0,
        completed_videos: videos.length,
        total_sensitive_detections: allDetections.length,
        high_risk_videos: highRiskVideos,
        recent_activity: recentActivity.slice(0, 10)
      }
    } catch (error) {
      console.error('获取仪表盘数据失败:', error)
      return {
        total_videos: 0, processing_videos: 0, completed_videos: 0,
        total_sensitive_detections: 0, high_risk_videos: 0, recent_activity: [], error: error.message
      }
    }
  },

  async aiChat(message) {
    try {
      const { invokeAIAgent } = await import('../utils/function-caller')
      const result = await invokeAIAgent('chat', message)
      if (result && result.response) {
        return { response: result.response, timestamp: result.timestamp || new Date().toISOString() }
      }
      throw new Error('返回结果格式错误')
    } catch (error) {
      console.error('AI对话失败:', error)
      throw new Error(`AI对话失败: ${error.message}`)
    }
  },

  async aiReset() {
    try {
      const { invokeAIAgent } = await import('../utils/function-caller')
      const result = await invokeAIAgent('reset', '')
      return { message: result.message || '对话已重置', success: true }
    } catch (error) {
      console.error('重置对话失败:', error)
      throw new Error(`重置失败: ${error.message}`)
    }
  }
}