import React from 'react'
import { translate } from 'react-i18next'
import Select from 'react-select'
import {
  addAllResourceI18n,
  CardPopup,
  createSpaceTree,
  CUSTOM_EVENT,
  SingleChoiceList,
  handleFetchResult,
  Popover,
  ROLE_LIST,
  sortWorkspaceList,
  sendGlobalFlashMessage,
  SPACE_TYPE,
  SPACE_TYPE_LIST,
  TracimComponent
} from 'tracim_frontend_lib'
import {
  getAllowedSpaceTypes,
  getUserSpaces,
  postSpace
} from '../action.async.js'
import i18n from '../i18n.js'
import { debug } from '../debug.js'

export class PopupCreateWorkspace extends React.Component {
  constructor (props) {
    super(props)

    const param = props.data || debug

    this.state = {
      appName: 'workspace',
      allowedTypes: [],
      config: param.config,
      isFirstStep: true,
      loggedUser: param.loggedUser,
      newDefaultRole: '',
      newParentSpace: {
        value: props.t('None'),
        label: props.t('None'),
        parentId: null,
        spaceId: null
      },
      newType: '',
      newName: '',
      parentOptions: [],
      showWarningMessage: false
    }

    // i18n has been init, add resources from frontend
    addAllResourceI18n(i18n, this.state.config.translation, this.state.loggedUser.lang)
    i18n.changeLanguage(this.state.loggedUser.lang)

    props.registerCustomEventHandlerList([
      { name: CUSTOM_EVENT.ALL_APP_CHANGE_LANGUAGE, handler: this.handleAllAppChangeLanguage }
    ])
  }

  // Custom Event Handlers
  handleAllAppChangeLanguage = data => {
    console.log('%c<PopupCreateWorkspace> Custom event', CUSTOM_EVENT.APP_CUSTOM_EVENT_LISTENER, data)
    this.setState(prev => ({
      loggedUser: {
        ...prev.loggedUser,
        lang: data
      }
    }))
    i18n.changeLanguage(data)
  }

  componentDidMount () {
    this.getTypeList()
  }

  handleChangeNewName = e => this.setState({ newName: e.target.value })

  handleChangeNewDefaultRole = newRole => this.setState({ newDefaultRole: newRole })

  handleChangeSpacesType = newType => this.setState({ newType: newType })

  handleChangeParentSpace = newParentSpace => this.setState({
    newParentSpace: newParentSpace,
    showWarningMessage: newParentSpace.parentId !== null
  })

  handleClickNextOrBack = async () => {
    const { props, state } = this

    if (state.isFirstStep) {
      const fetchGetUserSpaces = await handleFetchResult(await getUserSpaces(state.config.apiUrl, state.loggedUser.userId))

      switch (fetchGetUserSpaces.apiResponse.status) {
        case 200: {
          const spaceList = [{ value: props.t('None'), label: props.t('None'), parentId: null, spaceId: null }] // INFO - GB - 2020-10-07 - Root

          const addSpacesToList = (level, initialList) => {
            initialList.forEach(space => {
              const spaceType = SPACE_TYPE_LIST.find(type => type.slug === space.access_type)
              const spaceLabel = (
                <span title={space.label}>
                  {'-'.repeat(level)} <i className={`fa-fw ${spaceType.faIcon}`} /> {space.label}
                </span>
              )
              spaceList.push({ value: space.label, label: spaceLabel, parentId: space.parent_id, spaceId: space.workspace_id })
              if (space.children.length !== 0) addSpacesToList(level + 1, space.children)
            })
          }

          addSpacesToList(0, createSpaceTree(sortWorkspaceList(fetchGetUserSpaces.body)))

          this.setState({ parentOptions: spaceList, newParentSpace: spaceList[0], isFirstStep: false })
          break
        }
        default: sendGlobalFlashMessage(props.t('Error while getting user spaces')); break
      }
    } else this.setState({ isFirstStep: true })
  }

  handleClose = () => GLOBAL_dispatchEvent({
    type: CUSTOM_EVENT.HIDE_POPUP_CREATE_WORKSPACE, // handled by tracim_front:dist/index.html
    data: {
      name: this.state.appName
    }
  })

  handleValidate = async () => {
    const { props, state } = this

    const fetchPostSpace = await handleFetchResult(await postSpace(
      state.config.apiUrl,
      state.newDefaultRole,
      state.newParentSpace.spaceId,
      state.newName,
      state.newType
    ))

    switch (fetchPostSpace.apiResponse.status) {
      case 200:
        props.data.config.history.push(props.data.config.PAGE.WORKSPACE.DASHBOARD(fetchPostSpace.body.workspace_id))
        this.handleClose()
        break

      case 400:
        switch (fetchPostSpace.body.code) {
          case 2001: sendGlobalFlashMessage(props.t('Some input are invalid')); break
          case 3007: sendGlobalFlashMessage(props.t('A space with that name already exists')); break
          case 6001: sendGlobalFlashMessage(props.t('You cannot create anymore space')); break
          default: sendGlobalFlashMessage(props.t('Error while saving new space')); break
        }
        break
      default: sendGlobalFlashMessage(props.t('Error while saving new space')); break
    }
  }

  getTypeList = async () => {
    const fetchGetAllowedSpaceTypes = await handleFetchResult(await getAllowedSpaceTypes(this.state.config.apiUrl))

    switch (fetchGetAllowedSpaceTypes.apiResponse.status) {
      case 200: {
        const apiTypeList = fetchGetAllowedSpaceTypes.body.items
        const allowedTypesList = SPACE_TYPE_LIST.filter(type => apiTypeList.some(apiType => apiType === type.slug))
        this.setState({
          allowedTypes: allowedTypesList.map(type => ({ ...type, hexcolor: '' })),
          newType: (allowedTypesList.find(type => type.slug === SPACE_TYPE.confidential.slug) || allowedTypesList[0]).slug
        })
        break
      }
      default: sendGlobalFlashMessage(this.props.t('Error while saving new space')); break
    }
  }

  render () {
    const { props, state } = this
    const buttonStyleCallToAction = 'btn highlightBtn primaryColorBg primaryColorBorder primaryColorBgDarkenHover primaryColorBorderDarkenHover'
    const areParentSpacesVisible = state.config.system.config.ui__spaces__creation__parent_space_choice__visible

    return (
      <CardPopup
        customClass='newSpace'
        customColor={state.config.hexcolor}
        onClose={this.handleClose}
        faIcon={`fas fa-${state.config.faIcon}`}
        label={props.t('New space')}
      >
        <div className='newSpace__menu'>
          {state.isFirstStep
            ? (
              <>
                <div className='newSpace__label'> {props.t("Space's name:")} </div>
                <input
                  type='text'
                  className='newSpace__input'
                  placeholder={props.t("Space's name")}
                  value={state.newName}
                  onChange={this.handleChangeNewName}
                  onKeyDown={this.handleInputKeyDown}
                  autoFocus
                />

                {state.allowedTypes.length > 1 && (
                  <>
                    <div className='newSpace__label'> {props.t("Space's type:")} </div>
                    <SingleChoiceList
                      list={state.allowedTypes}
                      onChange={this.handleChangeSpacesType}
                      currentValue={state.newType}
                    />
                  </>
                )}

                <div className='newSpace__button'>
                  <button
                    className={buttonStyleCallToAction}
                    disabled={!state.newName || !state.newType}
                    onClick={this.handleClickNextOrBack}
                    title={props.t('Next')}
                    type='button'
                  >
                    {props.t('Next')} <i className='fas fa-arrow-right newSpace__icon__right' />
                  </button>
                </div>
              </>
            )
            : (
              <>
                {areParentSpacesVisible && (
                  <div>
                    <div className='newSpace__label'> {props.t('Parent space:')} </div>
                    <Select
                      className='newSpace__input'
                      isSearchable
                      onChange={this.handleChangeParentSpace}
                      options={state.parentOptions}
                      defaultValue={state.newParentSpace}
                    />
                    {state.showWarningMessage && (
                      <div className='newSpace__warningMessage'>
                        <i className='fas fa-exclamation-triangle slowblink newSpace__icon__left' style={{ color: state.config.hexcolor }} />
                        {props.t('Be careful, we do not recommend creating more than two levels of spaces because it makes the information much less accessible.')}
                      </div>
                    )}
                  </div>
                )}
                <div className='newSpace__label'>
                  {props.t('Default role:')}
                  <button
                    type='button'
                    className='btn transparentButton newSpace__label__info'
                    id='popoverDefaultRoleInfo'
                  >
                    <i className='fas fa-fw fa-question-circle' />
                  </button>

                  <Popover
                    targetId='popoverDefaultRoleInfo'
                    popoverBody={props.t('This is the role that members will have by default when they join your space (for open and on request spaces only).')}
                  />
                </div>

                <SingleChoiceList
                  list={ROLE_LIST}
                  onChange={this.handleChangeNewDefaultRole}
                  currentValue={state.newDefaultRole}
                />

                <div className='newSpace__button'>
                  <button
                    className='btn primaryColorBorder outlineTextBtn primaryColorBgHover primaryColorBorderDarkenHover newSpace__button__back'
                    disabled={!state.newName || state.newName.length === 0 || !state.newType || state.newType.length === 0}
                    onClick={this.handleClickNextOrBack}
                    title={props.t('Back')}
                    type='button'
                  >
                    <i className='fas fa-arrow-left newSpace__icon__left' /> {props.t('Back')}
                  </button>

                  <button
                    className={buttonStyleCallToAction}
                    disabled={!state.newDefaultRole}
                    onClick={this.handleValidate}
                    title={props.t('Create')}
                    type='button'
                  >
                    {props.t('Create')} <i className='fas fa-check newSpace__icon__right' />
                  </button>
                </div>
              </>
            )}
        </div>
      </CardPopup>
    )
  }
}

export default translate()(TracimComponent(PopupCreateWorkspace))
