/**
 * 华为云OBS客户端封装
 * 用于前端直接操作OBS，实现完全Serverless架构
 */
import ObsClient from 'esdk-obs-browserjs'

// OBS配置（从环境变量读取）
const OBS_CONFIG = {
  access_key_id: import.meta.env.VITE_HUAWEI_CLOUD_AK,
  secret_access_key: import.meta.env.VITE_HUAWEI_CLOUD_SK,
  server: import.meta.env.VITE_OBS_ENDPOINT || 'https://obs.cn-north-4.myhuaweicloud.com'
}

const BUCKET_NAME = import.meta.env.VITE_OBS_BUCKET_NAME || 'video-vault-storage'

// 初始化OBS客户端（单例模式）
let obsClient = null

export function initOBS() {
  if (!obsClient && OBS_CONFIG.access_key_id && OBS_CONFIG.secret_access_key) {
    obsClient = new ObsClient({
      access_key_id: OBS_CONFIG.access_key_id,
      secret_access_key: OBS_CONFIG.secret_access_key,
      server: OBS_CONFIG.server
    })
    console.log('OBS客户端初始化成功')
  }
  return obsClient
}

/**
 * 上传视频到OBS
 * @param {File} file - 视频文件
 * @param {Function} onProgress - 进度回调
 * @returns {Promise} 返回 {videoId, objectKey}
 */
export async function uploadVideoToOBS(file, onProgress) {
  const client = initOBS()
  if (!client) {
    throw new Error('OBS客户端未初始化，请检查环境变量配置')
  }

  // 生成视频ID（时间戳 + 文件名）
  const timestamp = Date.now()
  const fileName = file.name.replace(/\.[^/.]+$/, '').replace(/[^a-zA-Z0-9-_]/g, '_')
  const videoId = `${timestamp}-${fileName}`
  const objectKey = `uploads/${videoId}.mp4`

  console.log('===== 开始上传视频到OBS =====')
  console.log('文件名:', file.name)
  console.log('文件大小:', file.size, 'bytes')
  console.log('视频ID:', videoId)
  console.log('对象键:', objectKey)
  console.log('目标桶:', BUCKET_NAME)

  return new Promise((resolve, reject) => {
    client.putObject({
      Bucket: BUCKET_NAME,
      Key: objectKey,
      SourceFile: file,
      ProgressCallback: (transferredAmount, totalAmount, totalSeconds) => {
        const percent = Math.round((transferredAmount / totalAmount) * 100)
        if (onProgress) {
          onProgress(percent, transferredAmount, totalAmount, totalSeconds)
        }
      }
    }, (err, result) => {
      if (err) {
        console.error('[OBS] ❌ 上传失败:', err)
        reject(new Error(`上传失败: ${err.message || err.code}`))
      } else {
        console.log('[OBS] ✅ 上传成功!')
        console.log('[OBS] ETag:', result.InterfaceResult.ETag)
        console.log('[OBS] 现在等待OBS触发器启动 video-vault-slicer 云函数')
        resolve({ videoId, objectKey, etag: result.InterfaceResult.ETag })
      }
    })
  })
}

// /**
//  * 查询视频处理状态（检查outputs目录是否有结果）
//  * @param {string} videoId - 视频ID
//  * @returns {Promise} 返回状态对象
//  */
// export async function checkVideoStatus(videoId) {
//   const client = initOBS()
//   if (!client) {
//     throw new Error('OBS客户端未初始化')
//   }

//   console.log(`[OBS] 检查视频处理状态: ${videoId}`)

//   const outputKey = `outputs/${videoId}_sanitized.mp4`
//   const slicesPrefix = `slices/${videoId}/`
//   const auditLogKey = `logs/${videoId}_audit.json`

//   // 检查输出文件是否存在
//   return new Promise((resolve) => {
//     console.log(`[OBS] 正在检查输出文件: ${outputKey}`)

//     client.getObjectMetadata({
//       Bucket: BUCKET_NAME,
//       Key: outputKey
//     }, (err, result) => {
//       console.log('[OBS] getObjectMetadata 回调')
//       console.log('  - err:', err)
//       console.log('  - result status:', result?.status)
//       console.log('  - InterfaceResult:', result?.InterfaceResult)

//       // 浏览器版OBS SDK的404可能在result.status中
//       const is404 = err?.code === 'NoSuchKey' ||
//                     err?.code === '404' ||
//                     err?.code === 'NotFound' ||
//                     result?.status === 404 ||
//                     result?.InterfaceResult?.RequestId === undefined

//       if (err || is404) {
//         console.log(`[OBS] ❌ 输出文件不存在: ${outputKey}`)

//         // 检查中间步骤：切片是否生成
//         client.listObjects({
//             Bucket: BUCKET_NAME,
//             Prefix: slicesPrefix,
//             MaxKeys: 10
//           }, (sliceErr, sliceResult) => {
//             if (!sliceErr && sliceResult.InterfaceResult.Contents && sliceResult.InterfaceResult.Contents.length > 0) {
//               console.log(`[OBS] 找到 ${sliceResult.InterfaceResult.Contents.length} 个切片文件`)
//               console.log('[OBS] 切片文件列表:', sliceResult.InterfaceResult.Contents.map(c => c.Key))

//               // 检查审计日志
//               client.getObjectMetadata({
//                 Bucket: BUCKET_NAME,
//                 Key: auditLogKey
//               }, (auditErr, auditResult) => {
//                 if (!auditErr) {
//                   console.log(`[OBS] 审计日志已生成: ${auditLogKey}`)
//                   resolve({
//                     status: 'processing',
//                     exists: false,
//                     details: {
//                       slices_found: sliceResult.InterfaceResult.Contents.length,
//                       audit_log_exists: true,
//                       stage: 'merging'
//                     }
//                   })
//                 } else {
//                   console.log('[OBS] 审计日志尚未生成，DLP扫描进行中')
//                   resolve({
//                     status: 'processing',
//                     exists: false,
//                     details: {
//                       slices_found: sliceResult.InterfaceResult.Contents.length,
//                       audit_log_exists: false,
//                       stage: 'scanning'
//                     }
//                   })
//                 }
//               })
//             } else {
//               console.log('[OBS] 未找到切片文件，视频切分可能还未开始或失败')
//               resolve({
//                 status: 'processing',
//                 exists: false,
//                 details: {
//                   slices_found: 0,
//                   stage: 'slicing'
//                 }
//               })
//             }
//           })
//       } else {
//         // 文件存在且可访问，处理完成
//         if (result?.InterfaceResult?.ContentLength !== undefined) {
//           console.log(`[OBS] ✅ 输出文件已生成: ${outputKey}`)
//           console.log('[OBS] 文件大小:', result.InterfaceResult.ContentLength, 'bytes')
//           resolve({
//             status: 'completed',
//             exists: true,
//             size: result.InterfaceResult.ContentLength,
//             lastModified: result.InterfaceResult.LastModified
//           })
//         } else {
//           console.log('[OBS] ⚠️ 输出文件查询返回异常结果，视为处理中')
//           resolve({
//             status: 'processing',
//             exists: false,
//             details: { stage: 'unknown' }
//           })
//         }
//       }
//     })
//   })
// }

// /**
//  * 获取视频下载URL（临时签名URL）
//  * @param {string} videoId - 视频ID
//  * @param {number} expires - 有效期（秒），默认1小时
//  * @returns {Promise<string>} 下载URL
//  */
// export async function getVideoDownloadURL(videoId, expires = 3600) {
//   const client = initOBS()
//   if (!client) {
//     throw new Error('OBS客户端未初始化')
//   }

//   const outputKey = `outputs/${videoId}_sanitized.mp4`

//   return new Promise((resolve, reject) => {
//     client.createSignedUrlSync({
//       Method: 'GET',
//       Bucket: BUCKET_NAME,
//       Key: outputKey,
//       Expires: expires
//     }, (err, result) => {
//       if (err) {
//         console.error('生成下载URL失败:', err)
//         reject(new Error(`生成下载URL失败: ${err.message || err.code}`))
//       } else {
//         resolve(result.SignedUrl)
//       }
//     })
//   })
// }

/**
 * 查询视频处理状态（检查outputs目录是否有结果）- 修复版
 * @param {string} videoId - 视频ID
 * @returns {Promise} 返回状态对象
 */
export async function checkVideoStatus(videoId) {
  const client = initOBS()
  if (!client) {
    throw new Error('OBS客户端未初始化')
  }

  console.log(`[OBS] 检查视频处理状态: ${videoId}`)

  const outputKey = `outputs/${videoId}_sanitized.mp4`
  const slicesPrefix = `slices/${videoId}/`
  const auditLogKey = `logs/${videoId}_audit.json`

  return new Promise((resolve) => {
    console.log(`[OBS] 正在检查输出文件: ${outputKey}`)

    // ✅ 改用 listObjects 检查文件是否存在（更可靠）
    client.listObjects({
      Bucket: BUCKET_NAME,
      Prefix: outputKey,
      MaxKeys: 1
    }, (err, result) => {
      console.log('[OBS] listObjects 回调')
      console.log('  - err:', err)
      console.log('  - result:', JSON.stringify(result, null, 2))

      if (err) {
        console.error('[OBS] 查询失败:', err)
        resolve({ status: 'error', error: err.message })
        return
      }

      const contents = result?.InterfaceResult?.Contents || []
      const outputFile = contents.find(obj => obj.Key === outputKey)

      if (outputFile) {
        // ✅ 文件存在，处理完成
        console.log(`[OBS] ✅ 输出文件已生成: ${outputKey}`)
        console.log('[OBS] 文件大小:', outputFile.Size, 'bytes')
        resolve({
          status: 'completed',
          exists: true,
          size: outputFile.Size,
          lastModified: outputFile.LastModified
        })
        return
      }

      // 文件不存在，检查中间步骤
      console.log(`[OBS] ❌ 输出文件不存在: ${outputKey}`)

      // 检查切片是否生成
      client.listObjects({
        Bucket: BUCKET_NAME,
        Prefix: slicesPrefix,
        MaxKeys: 100
      }, (sliceErr, sliceResult) => {
        if (sliceErr) {
          console.error('[OBS] 查询切片失败:', sliceErr)
          resolve({ status: 'processing', exists: false, details: { stage: 'unknown' } })
          return
        }

        const slices = sliceResult?.InterfaceResult?.Contents || []
        console.log(`[OBS] 找到 ${slices.length} 个切片文件`)

        if (slices.length > 0) {
          console.log('[OBS] 切片文件列表:', slices.map(c => c.Key))

          // 检查审计日志
          client.listObjects({
            Bucket: BUCKET_NAME,
            Prefix: auditLogKey,
            MaxKeys: 1
          }, (auditErr, auditResult) => {
            const auditExists = (auditResult?.InterfaceResult?.Contents || []).length > 0

            if (auditExists) {
              console.log(`[OBS] 审计日志已生成: ${auditLogKey}`)
              resolve({
                status: 'processing',
                exists: false,
                details: {
                  slices_found: slices.length,
                  audit_log_exists: true,
                  stage: 'merging'
                }
              })
            } else {
              console.log('[OBS] 审计日志尚未生成，DLP扫描进行中')
              resolve({
                status: 'processing',
                exists: false,
                details: {
                  slices_found: slices.length,
                  audit_log_exists: false,
                  stage: 'scanning'
                }
              })
            }
          })
        } else {
          console.log('[OBS] 未找到切片文件，视频切分可能还未开始或失败')
          resolve({
            status: 'processing',
            exists: false,
            details: {
              slices_found: 0,
              stage: 'slicing'
            }
          })
        }
      })
    })
  })
}



/**
 * 获取视频下载URL（临时签名URL）- 修复版
 * @param {string} videoId - 视频ID
 * @param {number} expires - 有效期（秒），默认1小时
 * @returns {Promise<string>} 下载URL
 */
export async function getVideoDownloadURL(videoId, expires = 3600) {
  const client = initOBS()
  if (!client) {
    throw new Error('OBS客户端未初始化')
  }

  const outputKey = `outputs/${videoId}_sanitized.mp4`

  // ✅ 修复：createSignedUrlSync 是同步方法，直接返回结果
  // 不需要回调函数
  try {
    const result = client.createSignedUrlSync({
      Method: 'GET',
      Bucket: BUCKET_NAME,
      Key: outputKey,
      Expires: expires
    })

    console.log('[OBS] 生成下载URL成功:', result.SignedUrl?.substring(0, 80) + '...')
    return result.SignedUrl
  } catch (err) {
    console.error('[OBS] 生成下载URL失败:', err)
    throw new Error(`生成下载URL失败: ${err.message || err.code}`)
  }
}


/**
 * 列出所有处理完成的视频
 * @param {number} maxKeys - 最大返回数量
 * @returns {Promise<Array>} 视频列表
 */
export async function listProcessedVideos(maxKeys = 100) {
  const client = initOBS()
  if (!client) {
    throw new Error('OBS客户端未初始化')
  }

  return new Promise((resolve, reject) => {
    client.listObjects({
      Bucket: BUCKET_NAME,
      Prefix: 'outputs/',
      MaxKeys: maxKeys
    }, (err, result) => {
      if (err) {
        console.error('列出视频失败:', err)
        reject(new Error(`列出视频失败: ${err.message || err.code}`))
      } else {
        const videos = (result.InterfaceResult.Contents || [])
          .filter(obj => obj.Key.endsWith('_sanitized.mp4'))
          .map(obj => {
            const videoId = obj.Key.replace('outputs/', '').replace('_sanitized.mp4', '')
            return {
              videoId,
              key: obj.Key,
              size: obj.Size,
              lastModified: obj.LastModified,
              // 解析时间戳和文件名
              timestamp: videoId.split('-')[0],
              filename: videoId.split('-').slice(1).join('-')
            }
          })
          .sort((a, b) => new Date(b.lastModified) - new Date(a.lastModified))

        resolve(videos)
      }
    })
  })
}

// /**
//  * 获取审计日志（从OBS读取JSON）
//  * @param {string} videoId - 视频ID
//  * @returns {Promise<Object|null>} 审计日志对象
//  */
// export async function getAuditLog(videoId) {
//   const client = initOBS()
//   if (!client) {
//     throw new Error('OBS客户端未初始化')
//   }

//   const logKey = `logs/${videoId}_audit.json`

//   return new Promise((resolve) => {
//     client.getObject({
//       Bucket: BUCKET_NAME,
//       Key: logKey
//     }, (err, result) => {
//       if (err) {
//         if (err.code === 'NoSuchKey' || err.code === '404') {
//           resolve(null)  // 没有审计日志
//         } else {
//           console.error('读取审计日志失败:', err)
//           resolve(null)
//         }
//       } else {
//         try {
//           console.log('[OBS] 审计日志读取成功，Content类型:', typeof result.InterfaceResult.Content)

//           const content = result.InterfaceResult.Content

//           // 处理不同类型的返回值（浏览器版OBS SDK）
//           if (typeof content === 'string') {
//             // 直接是字符串
//             const logData = JSON.parse(content)
//             console.log('[OBS] 审计日志解析成功:', logData)
//             resolve(logData)
//           } else if (content instanceof Blob) {
//             // Blob 对象
//             const reader = new FileReader()
//             reader.onload = (e) => {
//               try {
//                 const logData = JSON.parse(e.target.result)
//                 console.log('[OBS] 审计日志解析成功（Blob）:', logData)
//                 resolve(logData)
//               } catch (parseErr) {
//                 console.error('[OBS] 解析审计日志失败:', parseErr)
//                 resolve(null)
//               }
//             }
//             reader.onerror = () => {
//               console.error('[OBS] 读取Blob内容失败')
//               resolve(null)
//             }
//             reader.readAsText(content)
//           } else if (content && content.toString) {
//             // 其他对象，尝试转字符串
//             const logData = JSON.parse(content.toString())
//             console.log('[OBS] 审计日志解析成功（toString）:', logData)
//             resolve(logData)
//           } else {
//             console.error('[OBS] 未知的Content类型:', content)
//             resolve(null)
//           }
//         } catch (err) {
//           console.error('[OBS] 处理审计日志失败:', err)
//           resolve(null)
//         }
//       }
//     })
//   })
// }


/**
 * 获取审计日志（从OBS读取JSON）- 修复版
 * @param {string} videoId - 视频ID
 * @returns {Promise<Object|null>} 审计日志对象
 */
export async function getAuditLog(videoId) {
  const client = initOBS()
  if (!client) {
    throw new Error('OBS客户端未初始化')
  }

  const logKey = `logs/${videoId}_audit.json`

  return new Promise((resolve) => {
    client.getObject({
      Bucket: BUCKET_NAME,
      Key: logKey
    }, (err, result) => {
      if (err) {
        if (err.code === 'NoSuchKey' || err.code === '404') {
          console.log(`[OBS] 审计日志不存在: ${logKey}`)
          resolve(null)
        } else {
          console.error('[OBS] 读取审计日志失败:', err)
          resolve(null)
        }
        return
      }

      try {
        const content = result.InterfaceResult.Content
        console.log('[OBS] 审计日志Content类型:', typeof content, content?.constructor?.name)

        // 1. 字符串：直接解析
        if (typeof content === 'string') {
          const logData = JSON.parse(content)
          console.log('[OBS] 审计日志解析成功（string），detections数量:', logData.detections?.length)
          resolve(logData)
          return
        }

        // 2. Blob：用 FileReader 读取
        if (content instanceof Blob) {
          const reader = new FileReader()
          reader.onload = (e) => {
            try {
              const logData = JSON.parse(e.target.result)
              console.log('[OBS] 审计日志解析成功（Blob），detections数量:', logData.detections?.length)
              resolve(logData)
            } catch (parseErr) {
              console.error('[OBS] 解析审计日志失败:', parseErr)
              resolve(null)
            }
          }
          reader.onerror = () => {
            console.error('[OBS] 读取Blob内容失败')
            resolve(null)
          }
          reader.readAsText(content)
          return
        }

        // 3. ArrayBuffer / Uint8Array：用 TextDecoder 解码
        if (content instanceof ArrayBuffer || content instanceof Uint8Array) {
          const decoder = new TextDecoder('utf-8')
          const text = decoder.decode(content)
          const logData = JSON.parse(text)
          console.log('[OBS] 审计日志解析成功（Binary），detections数量:', logData.detections?.length)
          resolve(logData)
          return
        }

        // 4. ✅ 已经是普通对象（SDK自动解析了JSON）：直接使用
        if (typeof content === 'object' && content !== null && !(content instanceof Blob)) {
          console.log('[OBS] 审计日志已是对象，detections数量:', content.detections?.length)
          resolve(content)
          return
        }

        // 5. 未知类型
        console.error('[OBS] 未知的Content类型:', typeof content, content)
        resolve(null)

      } catch (err) {
        console.error('[OBS] 处理审计日志失败:', err)
        resolve(null)
      }
    })
  })
}

/**
 * 删除视频及相关文件
 * @param {string} videoId - 视频ID
 * @returns {Promise<boolean>} 是否成功
 */
export async function deleteVideo(videoId) {
  const client = initOBS()
  if (!client) {
    throw new Error('OBS客户端未初始化')
  }

  const keysToDelete = [
    `outputs/${videoId}_sanitized.mp4`,
    `logs/${videoId}_audit.json`,
    `uploads/${videoId}.mp4`
  ]

  const deletePromises = keysToDelete.map(key => {
    return new Promise((resolve) => {
      client.deleteObject({
        Bucket: BUCKET_NAME,
        Key: key
      }, (err) => {
        if (err && err.code !== 'NoSuchKey') {
          console.error(`删除失败 ${key}:`, err)
        }
        resolve()  // 即使失败也继续
      })
    })
  })

  await Promise.all(deletePromises)
  return true
}

/**
 * 检查OBS配置是否正确
 * @returns {Promise<boolean>}
 */
export async function checkOBSConfig() {
  try {
    const client = initOBS()
    if (!client) {
      return false
    }

    // 尝试列出bucket内容
    return new Promise((resolve) => {
      client.listObjects({
        Bucket: BUCKET_NAME,
        MaxKeys: 1
      }, (err) => {
        resolve(!err)
      })
    })
  } catch (error) {
    console.error('OBS配置检查失败:', error)
    return false
  }
}
