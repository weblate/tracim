import React from 'react'
import { expect } from 'chai'
import { shallow } from 'enzyme'
import sinon from 'sinon'
import { UserSpacesConfig as UserSpacesConfigWithoutHOC } from '../../../src/component/Account/UserSpacesConfig.jsx'
import { userFromApi } from '../../hocMock/redux/user/user.js'
import { firstWorkspaceFromApi } from '../../fixture/workspace/firstWorkspace.js'

describe('<UserSpacesConfig />', () => {
  const onChangeSubscriptionNotifCallBack = sinon.spy()

  const props = {
    registerLiveMessageHandlerList: () => {},
    userToEditId: 0,
    onChangeSubscriptionNotif: onChangeSubscriptionNotifCallBack
  }

  const wrapper = shallow(<UserSpacesConfigWithoutHOC {...props} t={key => key} />)
  const workspaceList = [{
    memberList: [{
      user_id: 0,
      role: 'content-manager',
      do_notify: true
    }],
    workspace_id: 1,
    label: 'randomLabel1'
  }, {
    memberList: [{
      user_id: 1,
      role: 'workspace-manager',
      do_notify: true
    }, {
      user_id: 0,
      role: 'content-manager',
      do_notify: true
    }],
    workspace_id: 2,
    label: 'randomLabel2'
  }]

  wrapper.setState({ workspaceList })

  describe('static design', () => {
    it(`should display ${workspaceList.length} space`, () => {
      expect(wrapper.find('div.spaceconfig__table__role').length).to.equal(workspaceList.length)
    })

    it('should display labels of spaces', () => {
      for (let i = 0; i < workspaceList.length; i++) {
        expect(wrapper.find('div.spaceconfig__table__spacename').at(i)).to.text().equal(workspaceList[i].label)
      }
    })
  })

  describe('eventType space member', () => {
    describe('handleMemberModified', () => {
      it("should update member's notifications", () => {
        wrapper.setState({ workspaceList })
        const tlmData = {
          fields: {
            author: userFromApi,
            user: userFromApi,
            member: { role: 'workspace-manager', do_notify: false },
            workspace: { ...firstWorkspaceFromApi, workspace_id: 2 }
          }
        }
        wrapper.instance().handleMemberModified(tlmData)

        console.error(wrapper.state().workspaceList.find(
          space => space.workspace_id === tlmData.fields.workspace.workspace_id
        ).memberList, tlmData.fields.user.user_id, 'LOOL')
        const member = wrapper.state().workspaceList.find(
          space => space.workspace_id === tlmData.fields.workspace.workspace_id
        ).memberList.find(m => m.user_id === tlmData.fields.user.user_id)

        expect(member.do_notify).to.equal(tlmData.fields.member.do_notify)
      })
    })
  })
})
