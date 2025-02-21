import {
  TLM_ENTITY_TYPE as TLM_ET,
  TLM_CORE_EVENT_TYPE as TLM_CET,
  TLM_SUB_TYPE as TLM_ST,
  getContentComment,
  handleFetchResult,
  getContent,
  getContentPath
} from 'tracim_frontend_lib'

const createActivityEvent = (message) => {
  const [, eventType, subEntityType] = message.event_type.split('.')
  return {
    eventId: message.event_id,
    eventType: subEntityType === TLM_ST.COMMENT
      ? eventType === 'created' ? 'commented' : `comment ${eventType}`
      : eventType,
    author: message.fields.author,
    created: message.created
  }
}

const createSingleMessageActivity = (activityParams, messageList) => {
  const message = messageList[0]
  return {
    ...activityParams,
    eventList: [],
    commentList: [],
    newestMessage: message
  }
}

const getCommentList = async (content, apiUrl) => {
  const response = await handleFetchResult(await getContentComment(apiUrl, content.workspace_id, content.content_id))
  return response.apiResponse.status === 200 ? response.body.items : []
}

/**
 * DOC - SG - 2021-04-16
 * Create a content activity from a list of messages.
 * Can return null if a the content is not accessible anymore: as messages are an history,
 * the content can be inaccessible when calling this function.
 * This function assumes that the list is ordered from newest to oldest.
 */
const createContentActivity = async (activityParams, messageList, apiUrl) => {
  // INFO - RJ - 2021-08-23
  // Beware, a content may have been moved to another workspace or deleted, so
  // the workspace field of the messages might be outdated or the content
  // inaccessible. This should be kept in mind while working on this code
  const newestMessage = messageList[0]

  let content = newestMessage.fields.content

  if (content.content_type === TLM_ST.COMMENT) {
    // INFO - SG - 2021-04-16
    // We have to get the parent content as comments shall produce an activity
    // for it and not for the comment.
    const parentContentType = content.parent_content_type
    const parentId = content.parent_id
    if (!(parentContentType && parentId)) return null
    const response = await handleFetchResult(await getContent(apiUrl, parentId))
    if (!response.apiResponse.ok) return null
    content = response.body
  }

  const fetchGetContentPath = await handleFetchResult(
    await getContentPath(apiUrl, content.content_id)
  )

  if (!fetchGetContentPath.apiResponse.ok) return null

  const contentPath = fetchGetContentPath.body.items
  const commentList = await getCommentList(content, apiUrl)
  return {
    ...activityParams,
    eventList: [],
    commentList: commentList,
    newestMessage: newestMessage,
    content: content,
    contentPath: contentPath,
    contentAvailable: !!contentPath
  }
}

const getActivityParams = (message) => {
  const [entityType, coreEventType, subEntityType] = message.event_type.split('.')
  switch (entityType) {
    case TLM_ET.CONTENT: {
      if (subEntityType === TLM_ST.COMMENT && coreEventType !== TLM_CET.CREATED) return null
      const id = (subEntityType === TLM_ST.COMMENT)
        ? message.fields.content.parent_id
        : message.fields.content.content_id
      return { id: `${entityType}-${id}`, entityType: entityType }
    }
    case TLM_ET.MENTION: {
      const id = (message.fields.content.content_type === TLM_ST.COMMENT)
        ? message.fields.content.parent_id
        : message.fields.content.content_id
      return { id: `${TLM_ET.CONTENT}-${id}`, entityType: TLM_ET.CONTENT }
    }
    case TLM_ET.SHAREDSPACE_MEMBER:
    case TLM_ET.SHAREDSPACE_SUBSCRIPTION:
      return { id: `${entityType}-e${message.event_id}`, entityType: entityType }
  }
  return null
}

const createActivity = async (activityParams, activityMessageList, apiUrl) => {
  switch (activityParams.entityType) {
    case TLM_ET.CONTENT:
      return await createContentActivity(activityParams, activityMessageList, apiUrl)
    case TLM_ET.SHAREDSPACE_MEMBER:
    case TLM_ET.SHAREDSPACE_SUBSCRIPTION:
    default:
      return await createSingleMessageActivity(activityParams, activityMessageList)
  }
}

const groupMessageListByActivityId = (messageList) => {
  const activityMap = new Map()
  for (const message of messageList) {
    const activityParams = getActivityParams(message)
    if (activityParams !== null) {
      const activityParamsAndMessageList = activityMap.get(activityParams.id) || { list: [] }
      activityMap.set(activityParams.id, { params: activityParams, list: [...activityParamsAndMessageList.list, message] })
    }
  }

  return activityMap
}

const createActivityListFromActivityMap = async (activityMap, apiUrl) => {
  const activityCreationList = []
  for (const { params, list } of activityMap.values()) {
    activityCreationList.push(createActivity(params, list, apiUrl))
  }
  // NOTE - SG - 2020-11-19 - remove the null activities (can happen with content activities)
  return (await Promise.all(activityCreationList)).filter(i => i)
}

/**
 * Merge an activity list with message/TLM list
 * messages are assumed to be older.
 * Activities are returned in newest to oldest order.
 * INFO - SG - 2020-11-12 - this function assumes that the message list is already ordered from newest to oldest.
 */
export const mergeWithActivityList = async (messageList, activityList, apiUrl) => {
  const activityMap = groupMessageListByActivityId(messageList)

  for (const activity of activityList) {
    if (activityMap.has(activity.id)) {
      activityMap.delete(activity.id)
    }
  }

  const newActivityList = await createActivityListFromActivityMap(activityMap, apiUrl)
  return [...activityList, ...newActivityList]
}

/**
 * Sort an activity list from newest to oldest
 * Uses the newestMessage event_id attribute as the sort key.
 */
export const sortActivityList = (activityList) => {
  return [...activityList].sort((a, b) => b.newestMessage.event_id - a.newestMessage.event_id)
}

const updateActivity = (message, activity) => {
  const isComment = message.event_type.endsWith(`.${TLM_ST.COMMENT}`)
  const isMentionOnComment = (
    message.event_type.startsWith(`${TLM_ET.MENTION}.`) &&
    message.content.content_type === TLM_ST.COMMENT
  )
  // NOTE SG 2020-11-12: keep the existing content
  // if the message is a comment as a comment cannot change anything
  // on its parent
  // And update the comment list of the activity if it is one.
  return {
    ...activity,
    eventList: [
      createActivityEvent(message),
      ...activity.eventList
    ],
    commentList: isComment
      ? [...activity.commentList, message.fields.content]
      : activity.commentList,
    newestMessage: message,
    content: isComment || isMentionOnComment ? activity.content : message.fields.content
  }
}

/**
 * Add a message to an existing activity list.
 * If the message is not part of any activity, a new one will be created
 * and added at the beginning of the list
 * This WON'T re-order the list if the message is part of an existing
 * activity.
 * @param {*} message
 * @param {*} activityList
 */
export const addMessageToActivityList = async (message, activityList, apiUrl) => {
  const activityParams = getActivityParams(message)
  if (!activityParams) return activityList
  const activityIndex = activityList.findIndex(a => a.id === activityParams.id)
  if (activityIndex === -1) {
    const activity = await createActivity(activityParams, [message], apiUrl)
    return activity ? [activity, ...activityList] : activityList
  }
  const oldActivity = activityList[activityIndex]
  const updatedActivity = updateActivity(message, oldActivity)
  const updatedActivityList = [...activityList]
  updatedActivityList[activityIndex] = updatedActivity
  return updatedActivityList
}

/**
 * Set the event list of a given activity by building them from messages.
 * Does nothing if the activity is not in the given list
 * @param {str} activityId id of the activity to modify
 * @param {*} activityList list of activitiesx
 * @param {*} messageList list of messages for building events
 * @return updated activity
 */
export const setActivityEventList = (activityId, activityList, messageList) => {
  const activityIndex = activityList.findIndex(a => a.id === activityId)
  if (activityIndex === -1) return activityList
  const oldActivity = activityList[activityIndex]
  const updatedActivity = {
    ...oldActivity,
    eventList: messageList.map(createActivityEvent)
  }
  const updatedActivityList = [...activityList]
  updatedActivityList[activityIndex] = updatedActivity
  return updatedActivityList
}
