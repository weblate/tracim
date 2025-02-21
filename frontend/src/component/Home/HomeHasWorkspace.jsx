import React from 'react'
import { translate } from 'react-i18next'
import { Avatar, AVATAR_SIZE } from 'tracim_frontend_lib'
import { FETCH_CONFIG } from '../../util/helper.js'

require('./Home.styl')

// 2020-01-08 - RJ - NOTE
// This class is not used anymore since we redirect the user to their recent activities
// if they are a member of a workspace
// Leaving it there for now, should we revert this decision.
// See https://github.com/tracim/tracim/issues/4028

export const HomeHasWorkspace = props =>
  <div>
    <div className='homepagecard__title hasworkspace primaryColorFont'>
      {props.t('Welcome to Tracim')}
    </div>

    <div className='homepagecard__user'>
      <div className='homepagecard__user__avatar'>
        <Avatar
          size={AVATAR_SIZE.BIG}
          apiUrl={FETCH_CONFIG.apiUrl}
          user={props.user}
        />
      </div>

      <div className='homepagecard__user__publicname'>
        {props.user.publicName}
      </div>
    </div>

    <div className='homepagecard__delimiter delimiter primaryColorBg' />

    <div className='homepagecard__text'>
      {props.t('Please select a space in the left sidebar by clicking on it')}
    </div>

    <div className='homepagecard__endtext'>
      {props.t('Have a good day!')}
    </div>
  </div>

export default translate()(HomeHasWorkspace)
